# System Architecture Diagram

Mermaid version of the block diagram in
[`ARCHITECTURE.md`](../../ARCHITECTURE.md). Useful for slides, READMEs,
and as a reference while editing module boundaries.

---

## Components

```mermaid
flowchart TB
  subgraph Sensors["Sensors (on-device)"]
    CAM["Arducam IMX291<br/>USB camera"]
    DS["DS18B20<br/>1-Wire temp probe"]
  end

  subgraph Capture["src/capture/"]
    CAMMOD["camera.py<br/>FishCamera (OpenCV / V4L2)"]
    TEMPMOD["temperature.py<br/>DS18B20 reader"]
  end

  subgraph Inference["src/inference/ (Edge TPU)"]
    DET["detector.py<br/>FishDetector (TFLite + Coral)"]
    TRK["tracker.py<br/>CentroidTracker"]
    BEH["behavior.py<br/>BehaviorAnalyzer"]
  end

  subgraph DataLayer["src/data/"]
    DB[("SQLite<br/>fishfluencer.db")]
    IMG["image_manager.py<br/>(auto-purge, 24h TTL)"]
    SUM["summarizer.py<br/>Text summary"]
  end

  subgraph Social["src/social/"]
    POST["post_generator.py<br/>Claude API (text-only)"]
    PUB["publisher.py<br/>Platform adapters"]
  end

  subgraph Sync["src/sync/"]
    GH["github_sync.py<br/>OTA pull"]
    ERR["log_pusher.py<br/>Error report push"]
  end

  ORCH["src/main.py<br/>FishFluencer orchestrator<br/>(schedule)"]
  DASH["dashboard/<br/>HDMI display"]

  CAM --> CAMMOD
  DS --> TEMPMOD

  CAMMOD --> DET --> TRK --> BEH
  TEMPMOD --> DB
  BEH --> DB
  CAMMOD --> IMG
  IMG --> DB

  DB --> SUM --> POST --> PUB
  POST --> DB

  ORCH -.drives.-> CAMMOD
  ORCH -.drives.-> TEMPMOD
  ORCH -.drives.-> SUM
  ORCH -.drives.-> POST
  ORCH -.drives.-> IMG

  DB --> DASH
  ORCH --> ERR
  GH -.pulls.-> ORCH

  classDef hw fill:#1f2937,stroke:#60a5fa,color:#fff
  classDef edge fill:#0f766e,stroke:#5eead4,color:#fff
  classDef store fill:#7c2d12,stroke:#fdba74,color:#fff
  classDef ext fill:#4c1d95,stroke:#c4b5fd,color:#fff
  class CAM,DS hw
  class DET,TRK,BEH edge
  class DB,IMG store
  class POST,PUB,GH,ERR ext
```

---

## Trust boundary

The fundamental privacy property is that the camera frames and JPEG
snapshots stay inside the **on-device** boundary. Only text crosses
the line.

```mermaid
flowchart LR
  subgraph Device["On-device — Coral Dev Board"]
    direction TB
    F["Frames (RAM)"]
    J["JPEGs (24h TTL)"]
    M["Behavior + temp (SQLite)"]
    T["Text summary"]
  end

  subgraph External["External APIs"]
    direction TB
    CL["Claude API<br/>(text only)"]
    SM["Social platforms<br/>(text only)"]
    GHR["GitHub repo<br/>(code + sanitized error JSON)"]
  end

  F -.never leaves.-> F
  J -.never leaves.-> J
  M --> T
  T --> CL
  T --> SM
  M -. error reports .-> GHR

  classDef priv fill:#7f1d1d,stroke:#fca5a5,color:#fff
  classDef pub  fill:#065f46,stroke:#6ee7b7,color:#fff
  class F,J priv
  class CL,SM,GHR pub
```

| Data | Crosses boundary? |
|---|---|
| Raw frames / JPEGs | **No** |
| Detection bounding boxes | **No** |
| Behavior labels & temperature | Only as **text** inside a summary |
| API keys | **No** — systemd `Environment=` only |
| Error tracebacks | **Sanitized JSON** to a private repo branch |
