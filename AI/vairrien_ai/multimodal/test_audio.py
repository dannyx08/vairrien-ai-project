import asyncio

from vairrien_ai.multimodal.inference import MultimodalInference


async def main():
    multimodal = MultimodalInference()

    result = await multimodal.understand_audio(
        "vairrien_ai/multimodal/test.mp3",
        (
            "Analyze this audio accurately. "
            "Transcribe the speech if present, "
            "identify important sounds, and summarize "
            "the important information."
        ),
    )

    print("\n" + "=" * 60)
    print("AUDIO MULTIMODAL TEST")
    print("=" * 60)

    print("\nRAW RESULT:")
    print(result)

    print("\nSTATUS:", result.get("status"))
    print("MODEL:", result.get("model"))
    print("ERROR:", result.get("error"))
    print("\nCONTENT:")
    print(result.get("content"))

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())