"""Reporting behaviour at its public history/period boundary, with synthetic records."""

from datetime import date, datetime
import unittest

from custom_components.signinapp.reporting import (
    build_report,
    ReportingDataError,
    history_window,
    periods,
)
from custom_components.signinapp.quotas import ReportingOptions, quota_window


def clock(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def session(start, end, identity=1, changes=None):
    return {
        "id": identity,
        "siteId": 100,
        "inTimestamp": int(clock(start).timestamp()),
        "outTimestamp": int(clock(end).timestamp()) if end else None,
        "activityStatusChanges": changes
        if changes is not None
        else [change(start, 1, True)],
    }


def change(when, identity, working):
    return {
        "changedAt": when,
        "status": {
            "id": identity,
            "name": "Activity " + str(identity),
            "isWorking": working,
        },
    }


def report(rows, now="2026-11-04T18:00:00Z", config=None, **options):
    return build_report(
        rows,
        config or {"returningVisitor": {"status": "signed_out"}},
        clock(now),
        "Europe/London",
        ReportingOptions.from_mapping(options),
    )


class ReportingTests(unittest.TestCase):
    def test_multiple_sessions_and_breaks(self):
        rows = [
            session("2026-11-04T09:00:00Z", "2026-11-04T11:00:00Z"),
            session("2026-11-04T12:00:00Z", "2026-11-04T14:00:00Z", 2),
        ]
        r = report(rows, quota_rollups=True)["periods"]["today"]["values"]
        self.assertEqual(r["signed_in"], 4)
        self.assertEqual(r["working"], 4)
        self.assertEqual(r["session_count"], 2)
        self.assertEqual(r["quota_remaining"], 3.5)
        self.assertAlmostEqual(r["quota_percentage"], 4 / 7.5 * 100)

    def test_activity_break_not_working_quota(self):
        rows = [
            session(
                "2026-11-04T09:00:00Z",
                "2026-11-04T17:00:00Z",
                changes=[
                    change("2026-11-04T09:00:00Z", 1, True),
                    change("2026-11-04T12:00:00Z", 2, False),
                    change("2026-11-04T12:30:00Z", 1, True),
                ],
            )
        ]
        r = report(rows, quota_rollups=True)["periods"]["today"]
        self.assertEqual(r["values"]["signed_in"], 8)
        self.assertEqual(r["values"]["working"], 7.5)
        self.assertEqual(r["values"]["non_working"], 0.5)
        self.assertEqual(r["activities"]["2"], 0.5)
        self.assertEqual(r["values"]["quota_percentage"], 100)

    def test_midnight_split_and_sum(self):
        r = report([session("2026-11-03T23:00:00Z", "2026-11-04T02:00:00Z")])["periods"]
        self.assertEqual(r["tuesday"]["values"]["signed_in"], 1)
        self.assertEqual(r["wednesday"]["values"]["signed_in"], 2)
        self.assertEqual(r["week"]["values"]["signed_in"], 3)

    def test_spring_and_autumn_dst_elapsed_time(self):
        for start, end, now, expected in [
            (
                "2026-03-29T00:00:00Z",
                "2026-03-29T23:00:00Z",
                "2026-03-29T23:00:00Z",
                23,
            ),
            (
                "2026-10-24T23:00:00Z",
                "2026-10-26T00:00:00Z",
                "2026-10-26T00:00:00Z",
                25,
            ),
        ]:
            r = report([session(start, end)], now=now)["periods"]["yesterday"]["values"]
            self.assertEqual(r["signed_in"], expected)

    def test_duplicates_and_overlaps_not_double_counted(self):
        row = session("2026-11-04T09:00:00Z", "2026-11-04T12:00:00Z")
        other = session("2026-11-04T11:00:00Z", "2026-11-04T14:00:00Z", 2)
        self.assertEqual(
            report([row, row, other])["periods"]["today"]["values"]["signed_in"], 5
        )

    def test_conflicting_duplicate_rejected(self):
        with self.assertRaises(ReportingDataError):
            report(
                [
                    session("2026-11-04T09:00:00Z", "2026-11-04T12:00:00Z"),
                    session("2026-11-04T09:00:00Z", "2026-11-04T14:00:00Z"),
                ]
            )

    def test_overlap_with_contradictory_activity_is_unknown(self):
        rows = [
            session("2026-11-04T09:00:00Z", "2026-11-04T12:00:00Z"),
            session(
                "2026-11-04T11:00:00Z",
                "2026-11-04T13:00:00Z",
                2,
                [change("2026-11-04T11:00:00Z", 2, False)],
            ),
        ]
        v = report(rows)["periods"]["today"]["values"]
        self.assertEqual(v["signed_in"], 4)
        self.assertEqual(v["unclassified"], 1)
        self.assertIsNone(v["working"])

    def test_missing_activity_never_assumed_work(self):
        v = report(
            [session("2026-11-04T09:00:00Z", "2026-11-04T11:00:00Z", changes=[])],
            quota_rollups=True,
        )["periods"]["today"]["values"]
        self.assertEqual(v["signed_in"], 2)
        self.assertIsNone(v["working"])
        self.assertIsNone(v["quota_percentage"])

    def test_current_open_session_projects(self):
        cfg = {
            "returningVisitor": {
                "status": "signed_in",
                "lastIn": "2026-11-04T09:00:00Z",
            }
        }
        r = report([session("2026-11-04T09:00:00Z", None)], config=cfg)["periods"][
            "today"
        ]["values"]
        self.assertEqual(r["working"], 9)

    def test_open_session_missing_from_history_preserves_signed_in_only(self):
        cfg = {
            "returningVisitor": {
                "status": "signed_in",
                "lastIn": "2026-11-04T09:00:00Z",
            }
        }
        r = report([], config=cfg)["periods"]["today"]["values"]
        self.assertEqual(r["signed_in"], 9)
        self.assertIsNone(r["working"])

    def test_unconfirmed_open_session_rejected(self):
        with self.assertRaises(ReportingDataError):
            report([session("2026-11-04T09:00:00Z", None)])

    def test_new_type_and_name_change_stable_activity_key(self):
        row = session(
            "2026-11-04T09:00:00Z",
            "2026-11-04T10:00:00Z",
            changes=[change("2026-11-04T09:00:00Z", 42, True)],
        )
        r = report([row])
        self.assertEqual(r["periods"]["today"]["activities"]["42"], 1)
        row["activityStatusChanges"][0]["status"]["name"] = "Renamed"
        r = report([row])
        self.assertEqual(r["activities"]["42"]["name"], "Renamed")

    def test_default_quota_no_rollups(self):
        r = report([])["periods"]
        self.assertAlmostEqual(r["week"]["values"]["quota"], 37.5)
        self.assertIsNone(r["month"]["values"]["quota"])
        self.assertIsNone(r["today"]["values"]["quota"])

    def test_rollups_daily_and_monthly(self):
        r = report([], quota_rollups=True)["periods"]
        self.assertEqual(r["today"]["values"]["quota"], 7.5)
        self.assertEqual(r["month"]["values"]["quota"], 157.5)

    def test_holidays_opt_in_and_custom_dates(self):
        options = dict(
            quota_rollups=True, holiday_country="GB", holiday_subdivision="WLS"
        )
        normal = report([], now="2026-12-25T18:00:00Z", **options)["periods"]["today"][
            "values"
        ]
        adjusted = report(
            [], now="2026-12-25T18:00:00Z", holiday_adjustment=True, **options
        )["periods"]["today"]["values"]
        self.assertEqual(normal["quota"], 7.5)
        self.assertEqual(adjusted["quota"], 0)
        self.assertEqual(adjusted["quota_holiday_reduction"], 7.5)
        custom = report(
            [],
            holiday_adjustment=True,
            custom_holidays="2026-11-04",
            quota_rollups=True,
        )["periods"]["today"]["values"]
        self.assertEqual(custom["quota"], 0)

    def test_fortnight_and_ten_day_and_six_month(self):
        for unit, length, expected_days in [
            ("weeks", 2, 14),
            ("days", 10, 10),
            ("months", 6, None),
        ]:
            options = ReportingOptions.from_mapping(
                {
                    "quota_unit": unit,
                    "quota_length": length,
                    "quota_anchor": "2026-01-01" if unit != "weeks" else "2026-01-05",
                }
            )
            start, end = quota_window(date(2026, 11, 4), options)
            if expected_days:
                self.assertEqual((end - start).days, expected_days)
            else:
                self.assertEqual((start, end), (date(2026, 7, 1), date(2027, 1, 1)))
            self.assertLessEqual((end - start).days, 366)

    def test_monthly_base_rollup_varies_with_normal_workdays(self):
        r = report([], quota_unit="months", quota_hours=210, quota_rollups=True)[
            "periods"
        ]
        self.assertAlmostEqual(r["month"]["values"]["quota"], 210)
        self.assertAlmostEqual(r["today"]["values"]["quota"], 10)

    def test_zero_quota_and_overtime(self):
        v = report(
            [session("2026-11-04T09:00:00Z", "2026-11-04T10:00:00Z")],
            quota_hours=0,
            quota_rollups=True,
        )["periods"]["today"]["values"]
        self.assertEqual(v["quota_overtime"], 1)
        self.assertEqual(v["quota_remaining"], 0)
        self.assertIsNone(v["quota_percentage"])

    def test_monday_completed_week_and_month_boundary(self):
        p = {
            v.key: v
            for v in periods(
                clock("2027-02-01T00:00:00Z"), "Europe/London", ReportingOptions()
            )
        }
        self.assertEqual(p["week_to_yesterday"].start.date(), date(2027, 1, 25))
        self.assertEqual(p["week"].start.date(), date(2027, 2, 1))

    def test_history_window_covers_base_period(self):
        a, b = history_window(
            clock("2026-11-04T12:00:00Z"),
            "Europe/London",
            ReportingOptions.from_mapping({"quota_unit": "months", "quota_length": 6}),
        )
        self.assertEqual((a, b), (date(2026, 7, 1), date(2026, 11, 5)))

    def test_invalid_configuration(self):
        for data in [
            {"quota_hours": float("nan")},
            {"quota_length": 0},
            {"quota_unit": "months", "quota_anchor": "2026-01-03"},
            {"workdays": []},
            {"custom_holidays": "not-a-date"},
            {"holiday_country": "NOT_A_COUNTRY"},
        ]:
            with self.subTest(data=data), self.assertRaises((ValueError, TypeError)):
                ReportingOptions.from_mapping(data)

    def test_same_working_class_different_overlapping_activities(self):
        rows = [
            session("2026-11-04T09:00:00Z", "2026-11-04T12:00:00Z"),
            session(
                "2026-11-04T11:00:00Z",
                "2026-11-04T13:00:00Z",
                2,
                [change("2026-11-04T11:00:00Z", 2, True)],
            ),
        ]
        p = report(rows)["periods"]["today"]
        self.assertEqual(p["values"]["working"], 4)
        self.assertEqual(p["values"]["unclassified_activity"], 1)
        self.assertIsNone(p["activities"]["1"])

    def test_future_epoch_milliseconds_rejected(self):
        row = session("2026-11-04T09:00:00Z", "2026-11-04T12:00:00Z")
        row["inTimestamp"] *= 1000
        with self.assertRaises(ReportingDataError):
            report([row])

    def test_latest_activity_definition_overrides_old_historical_label(self):
        cfg = {
            "returningVisitor": {"status": "signed_out"},
            "activityStatuses": [{"id": 1, "name": "New label", "isWorking": True}],
        }
        r = report(
            [session("2026-11-04T09:00:00Z", "2026-11-04T10:00:00Z")], config=cfg
        )
        self.assertEqual(r["activities"]["1"]["name"], "New label")


if __name__ == "__main__":
    unittest.main()
