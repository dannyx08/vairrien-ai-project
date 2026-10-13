import asyncio
import json

from vairrien_ai.api.server import tools


async def main():
    result = await tools.execute(
        "multimodal_understand_image",
        file_path="vairrien_ai/multimodal/test.jpg",
        instruction=(
            "Describe this image accurately. "
            "Identify the main objects, visible text, "
            "and important visual details."
        ),
    )

    print()
    print("=" * 60)
    print("MULTIMODAL TOOL TEST")
    print("=" * 60)

    print("\nRAW RESULT:")
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    print("\nSTATUS:", result.get("status"))
    print("MODEL:", result.get("model"))
    print("ERROR:", result.get("error"))
    print("CONTENT:", result.get("content"))

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())