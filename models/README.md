# Models

Drop the compiled Edge TPU model here as `detect_fish_edgetpu.tflite`.
Keep `labels.txt` in sync with the model's class indices.

## Why this folder is empty in the repo

The model file is ~5–15 MB of binary weights and is **not** checked in —
each device should pull its model from a release asset, an LFS pointer,
or a local training run. The class labels (`labels.txt`) are committed
so the application can validate the model on first boot.

## Producing a model

The Edge TPU requires a **quantized TensorFlow Lite** model compiled
with the Edge TPU compiler:

1. Start with `ssd_mobilenet_v2` or `efficientdet-lite0` from the TF
   Model Zoo.
2. Fine-tune on fish data — your own tank footage, or public sets like
   [Fish4Knowledge](http://groups.inf.ed.ac.uk/f4k/) and
   [DeepFish](https://alzayats.github.io/DeepFish/).
3. Post-training quantize to INT8 (Edge TPU requirement).
4. Run `edgetpu_compiler model.tflite` to produce
   `model_edgetpu.tflite`.
5. Copy the compiled file here as `detect_fish_edgetpu.tflite` and
   update `labels.txt`.

For a smoke test before training your own model, the canonical
`ssd_mobilenet_v2_coco_quant_edgetpu.tflite` from
[coral.ai/models](https://coral.ai/models/object-detection/) works —
it just labels every fish as the nearest COCO class.
