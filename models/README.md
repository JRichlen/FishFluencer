# FishFluencer Models

Place your Edge TPU compiled TensorFlow Lite model files here.

## Required Files

| File | Description |
|------|-------------|
| `detect_fish_edgetpu.tflite` | Compiled Edge TPU fish detection model |
| `labels.txt` | Class labels (one per line) |

## Model Training

The Edge TPU requires a **quantized TensorFlow Lite** model compiled with the Edge TPU compiler.

### Recommended Approach

1. **Start with a pre-trained model** — Use `ssd_mobilenet_v2` or `efficientdet-lite0` from the TensorFlow Model Zoo
2. **Fine-tune on fish data** — Collect labeled images from your tank or use public datasets:
   - [Fish4Knowledge](http://groups.inf.ed.ac.uk/f4k/)
   - [DeepFish](https://alzayats.github.io/DeepFish/)
3. **Custom classes** — Train to detect your specific fish species plus tank objects (filter, heater, plants, decorations, food)
4. **Quantize** — Post-training quantization to INT8 (required for Edge TPU)
5. **Compile** — Run `edgetpu_compiler model.tflite` to produce the `_edgetpu.tflite` variant

A reasonable starting model can detect 5–10 object classes at ~30 FPS on the Edge TPU.
