# homeassistant-signinapp

> Generated from repository-local OKF records. The Markdown/YAML bundle remains canonical.

Source: `homeassistant-signinapp`

The report separates the connected repository map from detailed component and key-concept views so large bundles remain reviewable.

## Connected-area overview

```mermaid
flowchart LR
    a0["docs · 18 concepts"]
    a1["repository root · 3 concepts"]
    a2["tasks · 1 concepts"]
    a0 -->|links| a1
    a0 -->|links| a2
    a1 -->|links| a0
    a2 -->|links| a0
    classDef default fill:#eef2ff,stroke:#4f46e5,color:#1e1b4b
```

## Connected component 1

### docs

```mermaid
flowchart LR
    n0["Architecture"]:::boundary
    n1["Open-Ended Configured Location Model"]:::knowledge
    n2["Auth Model"]:::knowledge
    n3["Core Beliefs"]:::knowledge
    n4["Design"]:::knowledge
    n5["API Contract Discovery 2026-05-16"]:::knowledge
    n6["Verification Harness Completion"]:::knowledge
    n7["Tech Debt Tracker"]:::knowledge
    n8["homeassistant-signinapp complete Markdown inventory"]:::knowledge
    n9["homeassistant-signinapp documentation map"]:::knowledge
    n10["homeassistant-signinapp repository OKF visualization"]:::knowledge
    n11["Plans"]:::knowledge
    n12["Attendance Automation"]:::knowledge
    n13["Product Sense"]:::knowledge
    n14["Quality Score"]:::knowledge
    n15["Codebase Survey 2026-05-16"]:::knowledge
    n16["Observed API Contract 2026-05-16"]:::knowledge
    n17["Reliability"]:::knowledge
    n18["Security"]:::knowledge
    n19["Glossary"]:::boundary
    n20["Home Assistant Sign In App Integration"]:::boundary
    n21["Adopt RKE OKF knowledge format · done"]:::boundary
    n0 -->|links| n9
    n1 -->|links| n9
    n2 -->|links| n9
    n3 -->|links| n9
    n4 -->|links| n3
    n4 -->|links| n2
    n4 -->|links| n9
    n5 -->|links| n16
    n5 -->|links| n15
    n5 -->|links| n9
    n6 -->|links| n19
    n6 -->|links| n0
    n6 -->|links| n17
    n6 -->|links| n1
    n6 -->|links| n9
    n7 -->|links| n9
    n8 -->|links| n0
    n8 -->|links| n1
    n8 -->|links| n2
    n8 -->|links| n3
    n8 -->|links| n4
    n8 -->|links| n5
    n8 -->|links| n6
    n8 -->|links| n7
    n8 -->|links| n9
    n8 -->|links| n10
    n8 -->|links| n11
    n8 -->|links| n12
    n8 -->|links| n13
    n8 -->|links| n14
    n8 -->|links| n15
    n8 -->|links| n16
    n8 -->|links| n17
    n8 -->|links| n18
    n8 -->|links| n19
    n8 -->|links| n20
    n8 -->|links| n21
    n9 -->|links| n20
    n9 -->|links| n8
    n9 -->|links| n0
    n9 -->|links| n1
    n9 -->|links| n7
    n9 -->|links| n11
    n9 -->|links| n3
    n9 -->|links| n4
    n9 -->|links| n19
    n9 -->|links| n5
    n9 -->|links| n12
    n9 -->|links| n16
    n9 -->|links| n14
    n9 -->|links| n15
    n9 -->|links| n17
    n9 -->|links| n13
    n9 -->|links| n2
    n9 -->|links| n18
    n9 -->|links| n6
    n9 -->|links| n21
    n9 -->|links| n10
    n10 -->|links| n9
    n10 -->|links| n8
    n10 -->|links| n21
    n11 -->|links| n5
    n11 -->|links| n6
    n11 -->|links| n7
    n11 -->|links| n9
    n12 -->|links| n9
    n13 -->|links| n9
    n14 -->|links| n9
    n15 -->|links| n9
    n16 -->|links| n9
    n17 -->|links| n9
    n18 -->|links| n9
    n19 -->|links| n9
    n20 -->|links| n0
    n20 -->|links| n13
    n20 -->|links| n17
    n20 -->|links| n9
    n21 -->|links| n9
    n21 -->|links| n10
    classDef task fill:#dbeafe,stroke:#2563eb,color:#172554
    classDef workstream fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    classDef tracker fill:#ffedd5,stroke:#ea580c,color:#431407
    classDef knowledge fill:#dcfce7,stroke:#16a34a,color:#052e16
    classDef boundary fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-dasharray:4 3
```

### repository root

```mermaid
flowchart LR
    n0["Architecture"]:::knowledge
    n1["Verification Harness Completion"]:::boundary
    n2["homeassistant-signinapp complete Markdown inventory"]:::boundary
    n3["homeassistant-signinapp documentation map"]:::boundary
    n4["Product Sense"]:::boundary
    n5["Reliability"]:::boundary
    n6["Glossary"]:::knowledge
    n7["Home Assistant Sign In App Integration"]:::knowledge
    n0 -->|links| n3
    n1 -->|links| n6
    n1 -->|links| n0
    n1 -->|links| n5
    n1 -->|links| n3
    n2 -->|links| n0
    n2 -->|links| n1
    n2 -->|links| n3
    n2 -->|links| n4
    n2 -->|links| n5
    n2 -->|links| n6
    n2 -->|links| n7
    n3 -->|links| n7
    n3 -->|links| n2
    n3 -->|links| n0
    n3 -->|links| n6
    n3 -->|links| n5
    n3 -->|links| n4
    n3 -->|links| n1
    n4 -->|links| n3
    n5 -->|links| n3
    n6 -->|links| n3
    n7 -->|links| n0
    n7 -->|links| n4
    n7 -->|links| n5
    n7 -->|links| n3
    classDef task fill:#dbeafe,stroke:#2563eb,color:#172554
    classDef workstream fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    classDef tracker fill:#ffedd5,stroke:#ea580c,color:#431407
    classDef knowledge fill:#dcfce7,stroke:#16a34a,color:#052e16
    classDef boundary fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-dasharray:4 3
```

### tasks

```mermaid
flowchart LR
    n0["homeassistant-signinapp complete Markdown inventory"]:::boundary
    n1["homeassistant-signinapp documentation map"]:::boundary
    n2["homeassistant-signinapp repository OKF visualization"]:::boundary
    n3["Adopt RKE OKF knowledge format · done"]:::task
    n0 -->|links| n1
    n0 -->|links| n2
    n0 -->|links| n3
    n1 -->|links| n0
    n1 -->|links| n3
    n1 -->|links| n2
    n2 -->|links| n1
    n2 -->|links| n0
    n2 -->|links| n3
    n3 -->|links| n1
    n3 -->|links| n2
    classDef task fill:#dbeafe,stroke:#2563eb,color:#172554
    classDef workstream fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    classDef tracker fill:#ffedd5,stroke:#ea580c,color:#431407
    classDef knowledge fill:#dcfce7,stroke:#16a34a,color:#052e16
    classDef boundary fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-dasharray:4 3
```

## Key concept neighbourhoods

### homeassistant-signinapp documentation map

```mermaid
flowchart LR
    n0["Architecture"]:::boundary
    n1["Open-Ended Configured Location Model"]:::boundary
    n2["Auth Model"]:::boundary
    n3["Core Beliefs"]:::boundary
    n4["Design"]:::boundary
    n5["API Contract Discovery 2026-05-16"]:::boundary
    n6["Verification Harness Completion"]:::boundary
    n7["Tech Debt Tracker"]:::boundary
    n8["homeassistant-signinapp complete Markdown inventory"]:::boundary
    n9["homeassistant-signinapp documentation map"]:::knowledge
    n10["homeassistant-signinapp repository OKF visualization"]:::boundary
    n11["Plans"]:::boundary
    n12["Attendance Automation"]:::boundary
    n13["Product Sense"]:::boundary
    n14["Quality Score"]:::boundary
    n15["Codebase Survey 2026-05-16"]:::boundary
    n16["Observed API Contract 2026-05-16"]:::boundary
    n17["Reliability"]:::boundary
    n18["Security"]:::boundary
    n19["Glossary"]:::boundary
    n20["Home Assistant Sign In App Integration"]:::boundary
    n21["Adopt RKE OKF knowledge format · done"]:::boundary
    n0 -->|links| n9
    n1 -->|links| n9
    n2 -->|links| n9
    n3 -->|links| n9
    n4 -->|links| n3
    n4 -->|links| n2
    n4 -->|links| n9
    n5 -->|links| n16
    n5 -->|links| n15
    n5 -->|links| n9
    n6 -->|links| n19
    n6 -->|links| n0
    n6 -->|links| n17
    n6 -->|links| n1
    n6 -->|links| n9
    n7 -->|links| n9
    n8 -->|links| n0
    n8 -->|links| n1
    n8 -->|links| n2
    n8 -->|links| n3
    n8 -->|links| n4
    n8 -->|links| n5
    n8 -->|links| n6
    n8 -->|links| n7
    n8 -->|links| n9
    n8 -->|links| n10
    n8 -->|links| n11
    n8 -->|links| n12
    n8 -->|links| n13
    n8 -->|links| n14
    n8 -->|links| n15
    n8 -->|links| n16
    n8 -->|links| n17
    n8 -->|links| n18
    n8 -->|links| n19
    n8 -->|links| n20
    n8 -->|links| n21
    n9 -->|links| n20
    n9 -->|links| n8
    n9 -->|links| n0
    n9 -->|links| n1
    n9 -->|links| n7
    n9 -->|links| n11
    n9 -->|links| n3
    n9 -->|links| n4
    n9 -->|links| n19
    n9 -->|links| n5
    n9 -->|links| n12
    n9 -->|links| n16
    n9 -->|links| n14
    n9 -->|links| n15
    n9 -->|links| n17
    n9 -->|links| n13
    n9 -->|links| n2
    n9 -->|links| n18
    n9 -->|links| n6
    n9 -->|links| n21
    n9 -->|links| n10
    n10 -->|links| n9
    n10 -->|links| n8
    n10 -->|links| n21
    n11 -->|links| n5
    n11 -->|links| n6
    n11 -->|links| n7
    n11 -->|links| n9
    n12 -->|links| n9
    n13 -->|links| n9
    n14 -->|links| n9
    n15 -->|links| n9
    n16 -->|links| n9
    n17 -->|links| n9
    n18 -->|links| n9
    n19 -->|links| n9
    n20 -->|links| n0
    n20 -->|links| n13
    n20 -->|links| n17
    n20 -->|links| n9
    n21 -->|links| n9
    n21 -->|links| n10
    classDef task fill:#dbeafe,stroke:#2563eb,color:#172554
    classDef workstream fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    classDef tracker fill:#ffedd5,stroke:#ea580c,color:#431407
    classDef knowledge fill:#dcfce7,stroke:#16a34a,color:#052e16
    classDef boundary fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-dasharray:4 3
```

### homeassistant-signinapp complete Markdown inventory

```mermaid
flowchart LR
    n0["Architecture"]:::boundary
    n1["Open-Ended Configured Location Model"]:::boundary
    n2["Auth Model"]:::boundary
    n3["Core Beliefs"]:::boundary
    n4["Design"]:::boundary
    n5["API Contract Discovery 2026-05-16"]:::boundary
    n6["Verification Harness Completion"]:::boundary
    n7["Tech Debt Tracker"]:::boundary
    n8["homeassistant-signinapp complete Markdown inventory"]:::knowledge
    n9["homeassistant-signinapp documentation map"]:::boundary
    n10["homeassistant-signinapp repository OKF visualization"]:::boundary
    n11["Plans"]:::boundary
    n12["Attendance Automation"]:::boundary
    n13["Product Sense"]:::boundary
    n14["Quality Score"]:::boundary
    n15["Codebase Survey 2026-05-16"]:::boundary
    n16["Observed API Contract 2026-05-16"]:::boundary
    n17["Reliability"]:::boundary
    n18["Security"]:::boundary
    n19["Glossary"]:::boundary
    n20["Home Assistant Sign In App Integration"]:::boundary
    n21["Adopt RKE OKF knowledge format · done"]:::boundary
    n0 -->|links| n9
    n1 -->|links| n9
    n2 -->|links| n9
    n3 -->|links| n9
    n4 -->|links| n3
    n4 -->|links| n2
    n4 -->|links| n9
    n5 -->|links| n16
    n5 -->|links| n15
    n5 -->|links| n9
    n6 -->|links| n19
    n6 -->|links| n0
    n6 -->|links| n17
    n6 -->|links| n1
    n6 -->|links| n9
    n7 -->|links| n9
    n8 -->|links| n0
    n8 -->|links| n1
    n8 -->|links| n2
    n8 -->|links| n3
    n8 -->|links| n4
    n8 -->|links| n5
    n8 -->|links| n6
    n8 -->|links| n7
    n8 -->|links| n9
    n8 -->|links| n10
    n8 -->|links| n11
    n8 -->|links| n12
    n8 -->|links| n13
    n8 -->|links| n14
    n8 -->|links| n15
    n8 -->|links| n16
    n8 -->|links| n17
    n8 -->|links| n18
    n8 -->|links| n19
    n8 -->|links| n20
    n8 -->|links| n21
    n9 -->|links| n20
    n9 -->|links| n8
    n9 -->|links| n0
    n9 -->|links| n1
    n9 -->|links| n7
    n9 -->|links| n11
    n9 -->|links| n3
    n9 -->|links| n4
    n9 -->|links| n19
    n9 -->|links| n5
    n9 -->|links| n12
    n9 -->|links| n16
    n9 -->|links| n14
    n9 -->|links| n15
    n9 -->|links| n17
    n9 -->|links| n13
    n9 -->|links| n2
    n9 -->|links| n18
    n9 -->|links| n6
    n9 -->|links| n21
    n9 -->|links| n10
    n10 -->|links| n9
    n10 -->|links| n8
    n10 -->|links| n21
    n11 -->|links| n5
    n11 -->|links| n6
    n11 -->|links| n7
    n11 -->|links| n9
    n12 -->|links| n9
    n13 -->|links| n9
    n14 -->|links| n9
    n15 -->|links| n9
    n16 -->|links| n9
    n17 -->|links| n9
    n18 -->|links| n9
    n19 -->|links| n9
    n20 -->|links| n0
    n20 -->|links| n13
    n20 -->|links| n17
    n20 -->|links| n9
    n21 -->|links| n9
    n21 -->|links| n10
    classDef task fill:#dbeafe,stroke:#2563eb,color:#172554
    classDef workstream fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    classDef tracker fill:#ffedd5,stroke:#ea580c,color:#431407
    classDef knowledge fill:#dcfce7,stroke:#16a34a,color:#052e16
    classDef boundary fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-dasharray:4 3
```

### Verification Harness Completion

```mermaid
flowchart LR
    n0["Architecture"]:::boundary
    n1["Open-Ended Configured Location Model"]:::boundary
    n2["Verification Harness Completion"]:::knowledge
    n3["homeassistant-signinapp complete Markdown inventory"]:::boundary
    n4["homeassistant-signinapp documentation map"]:::boundary
    n5["Plans"]:::boundary
    n6["Reliability"]:::boundary
    n7["Glossary"]:::boundary
    n0 -->|links| n4
    n1 -->|links| n4
    n2 -->|links| n7
    n2 -->|links| n0
    n2 -->|links| n6
    n2 -->|links| n1
    n2 -->|links| n4
    n3 -->|links| n0
    n3 -->|links| n1
    n3 -->|links| n2
    n3 -->|links| n4
    n3 -->|links| n5
    n3 -->|links| n6
    n3 -->|links| n7
    n4 -->|links| n3
    n4 -->|links| n0
    n4 -->|links| n1
    n4 -->|links| n5
    n4 -->|links| n7
    n4 -->|links| n6
    n4 -->|links| n2
    n5 -->|links| n2
    n5 -->|links| n4
    n6 -->|links| n4
    n7 -->|links| n4
    classDef task fill:#dbeafe,stroke:#2563eb,color:#172554
    classDef workstream fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    classDef tracker fill:#ffedd5,stroke:#ea580c,color:#431407
    classDef knowledge fill:#dcfce7,stroke:#16a34a,color:#052e16
    classDef boundary fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-dasharray:4 3
```

### Home Assistant Sign In App Integration

```mermaid
flowchart LR
    n0["Architecture"]:::boundary
    n1["homeassistant-signinapp complete Markdown inventory"]:::boundary
    n2["homeassistant-signinapp documentation map"]:::boundary
    n3["Product Sense"]:::boundary
    n4["Reliability"]:::boundary
    n5["Home Assistant Sign In App Integration"]:::knowledge
    n0 -->|links| n2
    n1 -->|links| n0
    n1 -->|links| n2
    n1 -->|links| n3
    n1 -->|links| n4
    n1 -->|links| n5
    n2 -->|links| n5
    n2 -->|links| n1
    n2 -->|links| n0
    n2 -->|links| n4
    n2 -->|links| n3
    n3 -->|links| n2
    n4 -->|links| n2
    n5 -->|links| n0
    n5 -->|links| n3
    n5 -->|links| n4
    n5 -->|links| n2
    classDef task fill:#dbeafe,stroke:#2563eb,color:#172554
    classDef workstream fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    classDef tracker fill:#ffedd5,stroke:#ea580c,color:#431407
    classDef knowledge fill:#dcfce7,stroke:#16a34a,color:#052e16
    classDef boundary fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-dasharray:4 3
```

### Plans

```mermaid
flowchart LR
    n0["API Contract Discovery 2026-05-16"]:::boundary
    n1["Verification Harness Completion"]:::boundary
    n2["Tech Debt Tracker"]:::boundary
    n3["homeassistant-signinapp complete Markdown inventory"]:::boundary
    n4["homeassistant-signinapp documentation map"]:::boundary
    n5["Plans"]:::knowledge
    n0 -->|links| n4
    n1 -->|links| n4
    n2 -->|links| n4
    n3 -->|links| n0
    n3 -->|links| n1
    n3 -->|links| n2
    n3 -->|links| n4
    n3 -->|links| n5
    n4 -->|links| n3
    n4 -->|links| n2
    n4 -->|links| n5
    n4 -->|links| n0
    n4 -->|links| n1
    n5 -->|links| n0
    n5 -->|links| n1
    n5 -->|links| n2
    n5 -->|links| n4
    classDef task fill:#dbeafe,stroke:#2563eb,color:#172554
    classDef workstream fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    classDef tracker fill:#ffedd5,stroke:#ea580c,color:#431407
    classDef knowledge fill:#dcfce7,stroke:#16a34a,color:#052e16
    classDef boundary fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-dasharray:4 3
```

### API Contract Discovery 2026-05-16

```mermaid
flowchart LR
    n0["API Contract Discovery 2026-05-16"]:::knowledge
    n1["homeassistant-signinapp complete Markdown inventory"]:::boundary
    n2["homeassistant-signinapp documentation map"]:::boundary
    n3["Plans"]:::boundary
    n4["Codebase Survey 2026-05-16"]:::boundary
    n5["Observed API Contract 2026-05-16"]:::boundary
    n0 -->|links| n5
    n0 -->|links| n4
    n0 -->|links| n2
    n1 -->|links| n0
    n1 -->|links| n2
    n1 -->|links| n3
    n1 -->|links| n4
    n1 -->|links| n5
    n2 -->|links| n1
    n2 -->|links| n3
    n2 -->|links| n0
    n2 -->|links| n5
    n2 -->|links| n4
    n3 -->|links| n0
    n3 -->|links| n2
    n4 -->|links| n2
    n5 -->|links| n2
    classDef task fill:#dbeafe,stroke:#2563eb,color:#172554
    classDef workstream fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    classDef tracker fill:#ffedd5,stroke:#ea580c,color:#431407
    classDef knowledge fill:#dcfce7,stroke:#16a34a,color:#052e16
    classDef boundary fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-dasharray:4 3
```

## Legend

- Blue: task
- Purple: workstream
- Orange: tracker profile
- Green: durable knowledge
- Dashed neutral nodes: neighbouring context repeated from another area or key-concept view
- Time references: edges to addressable `Task.time[]` fragments
- Arrows: structured relationships or repository-local Markdown links
