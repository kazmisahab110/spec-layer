import json
from ollama import chat


def analyze_image(image_path: str):
    prompt = """
Identify the PRIMARY equipment/device in this image.

Return ONLY valid JSON:

{
    "device_type": "",
    "manufacturer": "",
    "model": null,
    "visible_text": [],
    "device_components": [],
    "nearby_objects": [],
    "uncertainties": []
}

IMPORTANT:
- device_components means physical parts that actually belong to the primary device.
- nearby_objects means objects visible in the image that are NOT part of the primary device.
- A keyboard, mouse, desk, computer, cable belonging to another device, etc. must NOT be classified as a component unless it physically belongs to the primary device.
- Do not guess internal components that are not visible.
- Do not guess manufacturer or model.
- If the exact model cannot be determined, use null.
IMPORTANT MODEL IDENTIFICATION RULES:
- Carefully inspect visible labels for explicit model identifiers.
- If visible text explicitly contains a model number, use that value
  for "model".
- For example, if the device label says "Model: P2726H",
  return "model": "P2726H".
- Do not return null when a model number is clearly printed on the
  equipment label.
- Do not infer a model from appearance alone.
"""

    response = chat(
        model="qwen2.5vl:7b",
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": [image_path],
            }
        ],
        options={
            "num_ctx": 8192
        }
    )

    content = response["message"]["content"]

    # Remove markdown fences if the model returns ```json ... ```
    content = content.replace("```json", "").replace("```", "").strip()

    return json.loads(content)


if __name__ == "__main__":
    image_path = input("Enter image path: ").strip().strip('"')

    result = analyze_image(image_path)

    print("\n=== QWEN VISION RESULT ===\n")
    print(json.dumps(result, indent=2))