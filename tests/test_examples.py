"""Validate generic examples without accessing a real account or phone."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from datetime import datetime
from zoneinfo import ZoneInfo

import yaml
from homeassistant import loader
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.template import Template

ROOT = Path(__file__).resolve().parents[1] / "examples"


def read(path):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


class ExampleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.tmp.name)
        loader.async_setup(self.hass)
        await self.hass.config.async_set_time_zone("Europe/London")

    async def asyncTearDown(self):
        await self.hass.async_stop(force=True)
        self.tmp.cleanup()

    def render(self, text, **variables):
        return Template(text, self.hass).async_render(variables)

    async def test_packages_validate_and_all_templates_compile(self):
        from homeassistant.components.automation.config import PLATFORM_SCHEMA

        count = 0
        for path in sorted((ROOT / "packages").glob("*.yaml")):
            package = yaml.safe_load(path.read_text(encoding="utf-8"))
            for automation in package["automation"]:
                PLATFORM_SCHEMA(automation)
                count += 1
            for value in walk(package):
                if isinstance(value, str) and ("{{" in value or "{%" in value):
                    Template(value, self.hass).ensure_valid()
        self.assertEqual(count, 9)

    async def test_custom_zone_membership_is_person_specific_and_unknown_is_not_exit(
        self,
    ):
        arrival, departure = read("packages/presence-custom-zone.yaml")["automation"]
        inside = arrival["conditions"][-1]["value_template"]
        outside = departure["conditions"][-1]["value_template"]
        self.hass.states.async_set(
            "sensor.customzone_campus",
            "1 in zone",
            {
                "trackers_in_zone": ["person.other"],
                "trackers_out_of_zone": [],
                "trackers_unusable": ["person.attendee"],
            },
        )
        self.assertFalse(self.render(inside))
        self.assertFalse(self.render(outside))
        self.hass.states.async_set(
            "sensor.customzone_campus",
            "1 in zone",
            {
                "trackers_in_zone": ["person.other"],
                "trackers_out_of_zone": ["person.attendee"],
            },
        )
        self.assertTrue(self.render(outside))
        self.hass.states.async_set("sensor.customzone_campus", "unavailable")
        self.assertFalse(self.render(outside))

    async def test_native_zone_requires_a_known_fresh_person(self):
        arrival, departure = read("packages/presence-zone.yaml")["automation"]
        inside = arrival["conditions"][-1]["value_template"]
        outside = departure["conditions"][-1]["value_template"]
        self.hass.states.async_set("zone.campus", "0", {"friendly_name": "Campus"})
        for state in ("unknown", "unavailable"):
            self.hass.states.async_set("person.attendee", state)
            self.assertFalse(self.render(inside))
            self.assertFalse(self.render(outside))
        self.hass.states.async_set(
            "person.attendee", "Campus", {"latitude": 51.0, "longitude": -1.0}
        )
        self.assertTrue(self.render(inside))
        self.assertFalse(self.render(outside))
        self.hass.states.async_set(
            "person.attendee", "not_home", {"latitude": 51.1, "longitude": -1.1}
        )
        self.assertTrue(self.render(outside))
        self.assertEqual(arrival["triggers"][0]["zone"], "zone.campus")
        self.assertEqual(departure["triggers"][0]["event"], "leave")

    async def test_notification_transitions_ignore_unknown_recovery(self):
        signed_in, signed_out = read("packages/attendance.yaml")["automation"][:2]
        for prior, current, expected in [
            ("unknown", "signed_in", False),
            ("unavailable", "signed_in", False),
            ("signed_out", "signed_in", True),
        ]:
            trigger = SimpleNamespace(
                from_state=State("sensor.attendee_status", prior),
                to_state=State(
                    "sensor.attendee_status", current, {"active_work_location_id": 1001}
                ),
            )
            self.assertEqual(
                self.render(
                    signed_in["conditions"][0]["value_template"], trigger=trigger
                ),
                expected,
            )
        trigger = SimpleNamespace(
            from_state=State("sensor.attendee_status", "signed_in"),
            to_state=State("sensor.attendee_status", "signed_out"),
        )
        self.assertTrue(
            self.render(signed_out["conditions"][0]["value_template"], trigger=trigger)
        )

    async def test_quarter_hour_rounding_is_presentation_only(self):
        automation = read("packages/attendance.yaml")["automation"][1]
        formatter = next(
            a["variables"]["total_words"]
            for a in automation["actions"]
            if "total_words" in a.get("variables", {})
        )
        for hours, expected in [
            (0, "0 minutes"),
            (8, "8 hours"),
            (8.125, "8 hours 15 minutes"),
            (8.12, "8 hours"),
            (None, "unavailable"),
        ]:
            self.assertEqual(self.render(formatter, total_hours=hours), expected)

    async def test_midnight_sign_out_uses_completed_day_and_previous_week(self):
        automation = read("packages/attendance.yaml")["automation"][1]
        selection = next(
            action["variables"]
            for action in automation["actions"]
            if "daily_entity" in action.get("variables", {})
        )
        midnight = datetime(2026, 1, 12, 0, 0, 1, tzinfo=ZoneInfo("Europe/London"))
        with patch("homeassistant.util.dt.now", return_value=midnight):
            variables = {"event_day": "2026-01-11", "event_week": "2026-01-05"}
            self.assertEqual(
                self.render(selection["daily_entity"], **variables),
                "sensor.attendee_yesterday_signed_in",
            )
            self.assertEqual(
                self.render(selection["weekly_entity"], **variables),
                "sensor.attendee_week_to_yesterday_signed_in",
            )

    async def test_notifications_keep_group_route_tags_and_cleanup(self):
        package = read("packages/attendance.yaml")
        sent, cleared = set(), set()
        for value in walk(package):
            if (
                not isinstance(value, dict)
                or value.get("action") != "notify.mobile_app_primary_phone"
            ):
                continue
            data = value["data"]
            if data["message"] == "clear_notification":
                cleared.add(data["data"]["tag"])
            else:
                sent.add(data["data"]["tag"])
                self.assertEqual(data["data"]["group"], "Sign In Updates")
                self.assertEqual(data["data"]["channel"], "Sign In Updates")
                self.assertEqual(data["data"]["clickAction"], "/lovelace/attendance")
                self.assertGreater(data["data"]["timeout"], 0)
        self.assertEqual(len(sent), 4)
        self.assertTrue(sent.issubset(cleared))

    async def test_dashboard_references_have_alias_metadata_and_private_visibility(
        self,
    ):
        dashboard = read("dashboard/attendance.yaml")
        aliases = read("dashboard/entity-aliases.yaml")
        for section in dashboard["views"][0]["sections"]:
            self.assertEqual(
                section["visibility"],
                [{"condition": "user", "users": ["REPLACE_WITH_HA_USER_ID"]}],
            )
        refs = {
            v["entity"]
            for v in walk(dashboard)
            if isinstance(v, dict) and isinstance(v.get("entity"), str)
        }
        reports = refs - {"sensor.attendee_status", "sensor.customzone_campus"}
        self.assertTrue(reports.issubset(aliases))
        self.assertGreaterEqual(len(reports), 100)
        for alias, metadata in aliases.items():
            self.assertTrue(alias.startswith("sensor.attendee_"))
            self.assertIn("report_period", metadata)
            self.assertIn("report_metric", metadata)

    @unittest.skipUnless(
        shutil.which("node"), "Node is needed to evaluate Button Card JavaScript"
    )
    async def test_nested_days_do_not_inherit_the_weekly_parent_value(self):
        dashboard = read("dashboard/attendance.yaml")
        parent = next(
            v
            for v in walk(dashboard)
            if isinstance(v, dict)
            and v.get("name") == "This week"
            and "custom_fields" in v
        )
        states = {parent["entity"]: {"state": "22"}}
        for i, day in enumerate(parent["custom_fields"]["days"]["card"]["cards"]):
            states[day["entity"]] = {"state": str([8, 7.75, 6.25, 0, 0, 0, 0][i])}
        source = """
const input=JSON.parse(require('fs').readFileSync(0,'utf8'));
const ActualDate=Date;global.Date=class extends ActualDate {
 constructor(...args){super(...(args.length?args:['2026-01-07T12:00:00Z']));}
};
const {parent,states}=input;const hass={config:{time_zone:'Europe/London'}};
function render(code,entity){return new Function('entity','states','hass',code.slice(3,-3))(entity,states,hass);}
let distinct=new Set();
for(const day of parent.custom_fields.days.card.cards){
 const a=render(day.state_display,states[day.entity]);
 const b=render(day.state_display,states[parent.entity]);
 if(a!==b)throw Error('Daily cell inherited weekly value');distinct.add(a);
}
if(distinct.size<3)throw Error('Daily cells collapsed into identical values');
if(render(parent.state_display,states[parent.entity])!=='22h')throw Error('Weekly value changed');
"""
        result = await self.hass.async_add_executor_job(
            lambda: subprocess.run(
                [shutil.which("node"), "-e", source],
                input=json.dumps({"parent": parent, "states": states}),
                text=True,
                capture_output=True,
                timeout=20,
            )
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
