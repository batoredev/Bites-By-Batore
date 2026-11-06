# Owned AI feasibility, resources and calculations

Prepared 6 November 2026. Research/proposal only: no provider switch, purchases, uploads, training run or product-scope reduction authorized or performed by this document. The existing local collector remains unchanged. Numbers labelled assumptions are engineering scenarios, not measured speed, vendor quotations or promised accuracy.

## 1. Meaning of ownership

Current checked configuration: local Ollama running qwen3-vl:2b-instruct, local faster-whisper using Whisper base, local SQLite and app/worker. The app's orchestration belongs to this project; Qwen/Whisper weights were developed elsewhere. Ollama is a runtime, not the learned intelligence. Removing Ollama can remove a software dependency without removing pretrained-model dependence.

Four different targets:

1. Independent operation without Codex/cloud AI: already supported locally.
2. No Ollama: serve compatible models directly through a local runtime; existing weights remain external.
3. Our application, datasets, training pipeline and weights: feasible with specialist models initialized from scratch, or a much more expensive general foundation-model program.
4. Every dependency invented/manufactured by us: would include operating system, compilers, ML libraries, GPU drivers/chips, internet and source platforms. That is not a practical application-project boundary. This proposal assumes open-source software algorithms are allowed, but the target learned weights are trained by us. This interpretation has not replaced the user's broader ownership requirement.

Fine-tuning Qwen is adaptation of someone else's base weights, not training all weights from scratch. Distilling from another model also introduces teacher dependence. Human labels, deterministic synthetic examples and appropriately sourced datasets are the strict from-scratch route. Public data is not automatically exclusively owned data.

Owning the AI does not mean owning Instagram availability or Google's place identity. If exact Google Maps names remain a requirement, retain a Maps verification input. Removing Google entirely would require a separate owned venue directory and mapping/routing-data strategy; no scope change is implied here.

## 2. Hardware actually inspected

- AMD Ryzen 5 5600H: 6 cores / 12 logical processors.
- RAM: 15.4 GiB visible, approximately 16 GB installed.
- NVIDIA RTX 3050 Laptop GPU: 4,096 MiB VRAM, confirmed by nvidia-smi.
- C: total 475.1 GiB, free 88.5 GiB at inspection.
- Current database: 51 source records, 46 active drafts, zero independently saved evaluation tasks. These source counts do not describe an adequate labelled training corpus.

This laptop can run the current collection/review system, classical ML, tiny-network prototypes and small batch experiments. It is a poor main training machine for broad ASR/OCR/video learning. Laptop GPU memory is fixed; RAM/SSD upgrade compatibility needs the laptop's exact model/service manual before buying anything.

## 3. Proposed architecture

Collector/scheduler -> local evidence store -> separate text/audio/frame specialists -> branch/entity resolver -> evidence database -> human approval -> itinerary planner. A second path takes reviewed examples into versioned datasets, training, evaluation, registry, shadow inference and approved deployment.

| Component | Owned implementation route | Training/input requirement |
|---|---|---|
| Discovery/collection | Existing durable queues, public adapters, dates, retries, pagination and dedup | No language model required for basic collection; source access remains external |
| Captions/comments | Character/word n-grams plus linear classifier; gazetteer/CRF extraction; optional small neural encoder later | Human classes and labelled name/address/price spans, including Tamil-English code switching |
| Speech | Random-initialized small Conformer/CTC or comparable recognizer trained in PyTorch/ESPnet | Transcribed speech, speaker splits, noisy reels and mixed-language data; replace Whisper only after passing tests |
| Visible text | Text-region detector and CTC recognizer trained from scratch | Real sign/menu crops plus rendered Tamil/English fonts with augmentation; real held-out tests |
| Food/vibe/activity visuals | Small CNN/multilabel network and timestamp aggregation | Actual labelled frames/sequences; vague claims such as crowd comfort require human grounding |
| Exact branch | Existing ORB/geometry, names, address components, coordinates, temporal evidence; optional own learned matcher | Same-branch and hard-negative pairs, chain branches and reused images |
| Creator history | Evidence-group statistics/calibration, not popularity as truth | Independent factual outcomes over time |
| Preference/planning | Own ranker/collaborative or content model; constrained route/budget/time solver; templated English explanation | Verified venues, explicit preferences, permissioned feedback; cold-start defaults |
| Corrections | Human review -> training examples -> offline experiment -> test -> model promotion | Corrections do not silently mutate production weights or become factual truth |

A general chat LLM is optional for this narrow architecture. Arbitrary open-ended dialogue, unrestricted-language understanding and broad video reasoning would require more modelling/data than these specialist pilots. Starting with English/Tamil is a proposed milestone, not cancellation of multilingual source support.

## 4. Software and deployment resources

- Python/FastAPI and the current worker contracts; FFmpeg/OpenCV/Playwright for media and collection.
- PyTorch for owned network training; scikit-learn for CPU models; ESPnet as an ASR implementation toolkit without importing pretrained checkpoints.
- SQLite initially; PostgreSQL/PostGIS if concurrency or geographic workloads justify migration. File/object storage for permitted datasets; versioned manifests and checksums.
- Local MLflow for experiments/model registry; an annotation UI for spans, transcripts, bounding boxes, branches and timestamps. The existing evaluation UI is a start, not a complete training-data management platform.
- Direct PyTorch serving initially; ONNX Runtime export only for supported and equivalence-tested models. A compatible language model could use llama.cpp, but custom architectures need implementation support.
- Linux workstation for dedicated GPU training; Windows remains usable for the existing app. Pin compatible Python/CUDA/driver/framework versions after a real GPU smoke test.
- Separate collection, review, training and serving workers. One physical GPU must be scheduled, not promised concurrently to every specialist. Keep API/review responsive on CPU.
- Package app and services, keep model weights versioned separately, use supervised restart/health checks, local-only admin access initially, rotating backups and tested restore. Add a second independent backup medium. Training datasets need an explicit retention policy separate from short-lived source caches.
- No automatic pretrained downloads or cloud fallback in the owned deployment. Test that inference works with network egress blocked; collection still requires internet.

## 5. Training data — first research targets, not guaranteed sufficiency

| Dataset | Initial target | Notes |
|---|---:|---|
| Comment/caption tasks | 20,000 reviewed items | Balance languages, classes, creators and negatives; span extraction may need additional labelling time |
| Real OCR/visual frames | 20,000 labelled frames/crops | Detailed boxes/scene annotation can take longer than the cost model below |
| Synthetic OCR lines | 200,000–1,000,000 | Own deterministic text rendering/augmentation; cannot replace real-world evaluation |
| Speech | 500 hours for a first narrow research pilot; potentially 2,000+ hours for stronger coverage | No promise 500 hours matches Whisper; include different speakers, noise and code switching |
| Branch pairs | 2,000 reviewed pairs | Hard negatives, chain branches, reused footage, changes over time |
| Release evaluation | At least 1,000 independent source groups as an initial proposed benchmark | Group by origin/creator/venue where appropriate; later-period test set; confidence intervals per language/task |

The 1,000-source benchmark is a proposed stricter dataset milestone; it does not silently change the currently coded provisional gates. Keep training, tuning and final test groups separate (e.g. 70/15/15), and reserve the final test set from correction retrieval and all training. Inspect licenses/permissions per actual dataset; AI4Bharat/IndicVoices is a potential data source, not a claim that all its audio is Tamil or transcribed or that acquisition is already approved.

Data volume example: 10,000 clips averaging 45 seconds contain only 125 audio hours. Reaching 500 hours at that length needs 40,000 clips if collecting all speech yourself. At 20 MB/clip, 100,000 clips are 2 TB before frames, models and copies. Two independent backups plus working data mean roughly 6 TB for raw bytes alone. Prefer targeted permitted training retention over saving every collected reel forever; this proposal does not change existing cache retention.

Annotation example, all rates assumed:

| Work | Calculation | Person-hours |
|---|---|---:|
| Text labels | 20,000 × 1 minute / 60 | 333.3 |
| Frame/crop labels | 20,000 × 45 seconds / 3,600 | 250 |
| Speech transcription | 500 audio hours × 6 person-hours/hour | 3,000 |
| Branch pairs | 2,000 × 3 minutes / 60 | 100 |
| Total plus 25% QA | 3,683.3 × 1.25 | 4,604.2 |

At an assumed INR 200/person-hour: INR 920,833, approximately **9.21 lakh**. This excludes acquiring/recording data, travel, licensing, translation, detailed bounding-box work and disputes beyond the QA allowance. Four annotators delivering 140 productive hours/month each would need about 8.2 months for this work. Already-labelled suitable datasets can reduce the workload; checking domain suitability remains necessary.

## 6. Hardware tiers and memory arithmetic

| Tier | Proposed resources | Planning capital allowance, not a quote |
|---|---|---|
| Current machine | Existing laptop + external backup; small CPU models and review | Existing hardware; upgrades priced only after compatibility checks |
| Specialist-model workstation | 24–32 GB NVIDIA GPU, 64–128 GB RAM, 12–16 CPU cores, 2 TB NVMe working disk, 4–8 TB data disk, independent backup, appropriate PSU/cooling/UPS | INR 3–6 lakh; obtain actual complete-system quotes |
| Larger training workstation/server | 2–4 GPUs with 48–80 GB each, 256–512 GB RAM, 4–8 TB NVMe plus 16 TB archive/backup, suitable PCIe lanes/cooling/power | Supplier-quoted project; do not extrapolate consumer-card prices into a server quote |
| General-model distributed runs | 4–8 interconnected 80 GB GPUs or more, 512 GB–1 TB host RAM, fast local NVMe; interconnect benchmark | Separate research purchase/rental decision, not authorized |

RTX 5090 is an example 32 GB card with 575 W graphics power according to NVIDIA. A whole training PC can draw more. Two cards do not automatically present one larger memory pool; explicit sharding is required. Hardware tier is a starting experiment capacity, not an assurance of model throughput or fit.

Mixed-precision Adam training planning approximation: 18 bytes/parameter for parameters/master weights/gradients/optimizer states, before activations, workspaces and batch-dependent memory. Actual implementations vary. 100M parameters -> 1.8 GB static state; 300M -> 5.4 GB; 1B -> 18 GB; 3B -> 54 GB. This explains why a 4 GB inference-capable laptop is not a broad training workstation. Quantized inference weights may be much smaller but do not represent full-training memory.

## 7. General text model from scratch: illustrative compute

This is a separate option, not necessary for the first specialist architecture and not a multimodal project quote.

Assumptions: dense Transformer training C ≈ 6ND, N parameters, D tokens; illustrative D=20N; sustained useful throughput=100 TFLOP/s per GPU. This throughput is an unmeasured modelling assumption, not a hardware benchmark or peak-spec estimate. The 20-token ratio is a rough scaling-law reference, not a modern quality guarantee; high-quality small models can use far more data.

GPU-hours = 6ND / (100 × 10^12 × 3,600).

For a cost comparison only, Runpod's fetched advertised H100 SXM rate was USD 3.99/GPU-hour. Currency assumption INR 90/USD is a planning conversion, **not a verified current exchange quote**. Taxes, storage, acquisition, restart loss, validation and multi-GPU communication overhead are excluded. Local-only preference remains in force; no remote training is proposed for immediate execution.

| Text model | Tokens | FLOPs | Equivalent GPU-hours | One-pass compute at assumptions |
|---|---:|---:|---:|---:|
| 300M | 6 billion | 1.08e19 | 30 | INR 10,773 |
| 1B | 20 billion | 1.20e20 | 333.3 | INR 119,700 |
| 3B | 60 billion | 1.08e21 | 3,000 | INR 1,077,300 |

At 50 TFLOP/s these times/costs double; at 200 TFLOP/s they halve, if memory and throughput actually permit. Eight GPUs at 70% scaling efficiency divide the single-GPU-equivalent time by 5.6, while billed aggregate GPU-hours increase by 1/0.7. For the 3B row: about 22.3 days and INR 15.39 lakh aggregate compute. This excludes all vision/audio training and does not promise a useful assistant.

Five to ten equivalent training runs across experiments would make the single-GPU-equivalent 1B text compute INR 5.99–11.97 lakh, or 3B INR 53.87 lakh–1.08 crore, before the other costs. Real experiment programs include smaller pilots as well as full runs. Do not budget an entire owned multimodal system from the cost of one dense text-model pass.

## 8. Operating budget, capacity and total project example

Electricity is an assumed INR 10/kWh, not a checked local tariff; measure wall draw and use the actual bill before purchase decisions.

- Laptop at 100 W average continuously: 0.1 × 24 × 30 × 10 = **INR 720/month**.
- Workstation at 700 W for 8 hours plus 80 W idle for 16 hours daily: (0.7×8 + 0.08×16)×30×10 = **INR 2,064/month**.
- Same workstation at 700 W continuously: 0.7×24×30×10 = **INR 5,040/month**.

These exclude cooling, internet, replacement/backup disks, hardware depreciation, people and external data services. A INR 4 lakh workstation amortized over 36 months adds INR 11,111/month of economic cost even if it is already paid for. The current INR 3,000/month operating target can support a small existing-machine pilot under suitable actual costs, not finance the proposed owned-model R&D program.

For comparison, a continuously rented H100 SXM at the above assumptions is 3.99×90×720 = INR 258,552/month before extras. This is why always-on training-class cloud hardware is inconsistent with the present budget.

Throughput is not established yet. Example only: with 120 GPU-seconds/reel, eight processing hours/day and 70% productive time, 8×3,600×0.7/120 = **168 reels/day**. If each takes 600 seconds, capacity falls to about 34/day. Source access, CPU decoding, ASR and other queues can reduce it further. Measure 100 representative reels on the intended pipeline before choosing hardware or collector limits. Deduplicate and cache; analyse newly changed evidence rather than rerunning every model on every source every day.

Paid-team narrow R&D pilot example, deliberately separate from ongoing operating cost:

| Item | Assumption | INR lakh |
|---|---|---:|
| Workstation/storage/backup allowance | Planning midpoint; quote required | 4.00 |
| Engineers | 3 engineers × 6 months × INR 150,000/month loaded cost | 27.00 |
| Annotation | Above 500-hour-speech scenario | 9.21 |
| Six-month operating/consumables allowance | Assumed INR 10,000/month | 0.60 |
| Subtotal | | 40.81 |
| Contingency | 25% | 10.20 |
| Total scenario | | **51.01** |

This is a roughly **INR 51 lakh research-pilot scenario**, not a market salary quote or a fixed-price promise to finish all languages. Data licensing/field acquisition and a general multimodal foundation model are excluded. Founder labour may reduce cash spend but does not remove person-hours or uncertainty. If the quality gates fail, more data and research are required. Do not spend this amount before a small pilot demonstrates that the architecture works.

## 9. Implementation, testing and staged deployment

1. **Baseline/data protocol, estimated 2–4 weeks:** instrument latency, memory, power and error categories; define training rights/retention and task labels; collect human reference answers. Keep existing local models as a baseline while research runs separately. If zero other-model use must apply immediately, disable those tasks and send them to manual review until replacements pass; silently preserving their capabilities is impossible.
2. **First owned text/planning models, estimated 4–8 weeks:** implement CPU classifiers, entity matching, dedup and preference ranking; build versioned datasets/checkpoints; replace only components that pass tests.
3. **Owned OCR/vision/branch experiments, estimated 2–4 months:** data and model iterations, hard-negative evaluation, visual references and temporal aggregation. These dates overlap data collection and are estimates for a staffed effort.
4. **Owned speech, estimated 3–9+ months:** train on properly sourced transcribed speech; evaluate Tamil/English/mixed speech, noise and venue-name errors. General multilingual expansion requires separate data and validation. No guaranteed deadline.
5. **System validation and deployment, estimated 4–8 weeks after models pass:** replay real cases, shadow comparisons, limited operator rollout, restore/rollback test, then invited users after the existing approvals. A narrow owned-specialist research pilot is a 6–12+ month planning horizon with overlapping work, not a delivery commitment for the complete original vision.

Test levels:

- Unit/integration: parsing, ownership, dedup, queues, quotas, source removal, budget arithmetic and publication invariants.
- Model: per-language name precision/recall, OCR character error, ASR word error, comment macro-F1/confusions, branch false-merge and abstention rates, confidence calibration and paired correction changes with uncertainty intervals.
- Independence: source/repost/speaker/venue/creator leakage checks; later-time holdout; exclude held-out corrections from retrieval/training. Never use model predictions as independent gold labels.
- Operational: GPU out-of-memory, process restart, network loss, changed page markup, stale facts, corrupted models, disk exhaustion and restore. The worker must preserve unfinished sources and refuse unsupported inferences.
- Promotion: versioned candidate -> frozen tests -> shadow mode -> explicit operator promotion -> rollbackable deployment. Updates cannot approve a location or bypass human review.
- Ownership: artifact hashes, data provenance, initialization records, dependency inventory; no hidden pretrained weights or external model endpoints in the owned inference path.

Staff capabilities needed: backend/data engineering, speech/vision ML training, evaluation/MLOps, and Tamil-English reviewers. Three engineering roles in the budget are a staffing scenario; one person can cover multiple roles more slowly. The current app already supplies orchestration and review foundations; owned training infrastructure, corpora and weights are still new work.

## 10. Sources checked

- Ollama local runtime API: https://docs.ollama.com/api/introduction
- Qwen model identity and serving examples: https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct
- Whisper code/models: https://github.com/openai/whisper
- NVIDIA RTX 5090 memory/power specifications: https://www.nvidia.com/en-in/geforce/graphics-cards/50-series/rtx-5090/
- Advertised GPU rental reference, fetched 6 November 2026: https://www.runpod.io/pricing
- Dense-model scaling reference: https://arxiv.org/abs/2203.15556
- Training memory anatomy: https://huggingface.co/docs/transformers/model_memory_anatomy
- PyTorch sharding: https://docs.pytorch.org/docs/2.15/fsdp.html
- Traditional classifiers: https://scikit-learn.org/stable/modules/linear_model.html
- Speech training toolkit: https://github.com/espnet/espnet
- Speech dataset research, not a substitute for checking the actual release/license: https://arxiv.org/abs/2403.01926
- Local deployment: https://onnxruntime.ai/docs/
- Experiment registry: https://mlflow.org/docs/latest/ml/
- Compatible language-model runtime alternative: https://github.com/ggml-org/llama.cpp
- Constraint-based itinerary building reference: https://developers.google.com/optimization/routing/vrptw

No model accuracy, current hardware price, actual electricity tariff, currency exchange rate or total delivery guarantee is inferred from these references. Those not measured/quoted are explicitly assumed above.
