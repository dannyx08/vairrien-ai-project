import asyncio

from vairrien_ai.multimodal.inference import MultimodalInference


async def main():
    multimodal = MultimodalInference()

    result = await multimodal.understand_image(
        "vairrien_ai/multimodal/test.jpg",
        (
            "Describe this image accurately. "
            "Identify the main objects, visible text, "
            "and important details."
        ),
    )

    print("\nSTATUS:", result["status"])
    print("MODEL:", result["model"])
    print("\nUNDERSTANDING:")
    print(result["content"])


if __name__ == "__main__":
    asyncio.run(main())