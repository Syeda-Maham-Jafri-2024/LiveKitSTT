# import asyncio
# import logging

# from dotenv import load_dotenv
# from livekit import rtc
# from livekit.agents import (
#     AutoSubscribe,
#     JobContext,
#     WorkerOptions,
#     cli,
#     stt,
#     transcription,
# )
# from livekit.plugins import openai, assemblyai
# from livekit.plugins.openai import stt


# load_dotenv()

# logger = logging.getLogger("transcriber")

# async def entrypoint(ctx: JobContext):
#     logger.info(f"Starting transcriber (speech to text) example, room: {ctx.room.name}")
#     stt_impl = assemblyai.STT()

#     @ctx.room.on("track_subscribed")
#     def on_track_subscribed(
#         track: rtc.Track,
#         publication: rtc.TrackPublication,
#         participant: rtc.RemoteParticipant,
#     ):
#         if track.kind == rtc.TrackKind.KIND_AUDIO:
#             asyncio.create_task(transcribe_track(participant, track))

#     async def transcribe_track(participant: rtc.RemoteParticipant, track: rtc.Track):
#         """
#         Handles the parallel tasks of sending audio to the STT service and 
#         forwarding transcriptions back to the app.
#         """
#         audio_stream = rtc.AudioStream(track)
#         stt_forwarder = transcription.STTSegmentsForwarder(
#             room=ctx.room, participant=participant, track=track
#         )

#         stt_stream = stt_impl.stream()

#         # Run tasks for audio input and transcription output in parallel
#         await asyncio.gather(
#             _handle_audio_input(audio_stream, stt_stream),
#             _handle_transcription_output(stt_stream, stt_forwarder),
#         )

#     async def _handle_audio_input(
#         audio_stream: rtc.AudioStream, stt_stream: stt.SpeechStream
#     ):
#         """Pushes audio frames to the speech-to-text stream."""
#         async for ev in audio_stream:
#             stt_stream.push_frame(ev.frame)

#     async def _handle_transcription_output(
#         stt_stream: stt.SpeechStream, stt_forwarder: transcription.STTSegmentsForwarder
#     ):
#         """Receives transcription events from the speech-to-text service."""
#         async for ev in stt_stream:
#             if ev.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
#                 print(" -> ", ev.alternatives[0].text)

#             stt_forwarder.update(ev)

#     await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)


# if __name__ == "__main__":
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


import asyncio
import logging
import openai
from openai import OpenAI
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    transcription,
)
import os
import io
from pydub import AudioSegment

load_dotenv()

# Ensure to set your OpenAI API key
openai_api_key = os.getenv("OPENAI_API_KEY")

logger = logging.getLogger("transcriber")

async def entrypoint(ctx: JobContext):
    logger.info(f"Starting transcriber (speech to text), room: {ctx.room.name}")

    @ctx.room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.Track,
        publication: rtc.TrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        logger.info(f"Track subscribed: {track.kind}, participant: {participant.identity}")
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info(f"Audio track subscribed, participant: {participant.identity}")
            asyncio.create_task(transcribe_track(participant, track))

    async def transcribe_track(participant: rtc.RemoteParticipant, track: rtc.Track):
        """Handles the parallel tasks of sending audio to the STT service."""
        logger.info("Starting audio transcription task...")
        audio_stream = rtc.AudioStream(track)
        stt_forwarder = transcription.STTSegmentsForwarder(
            room=ctx.room, participant=participant, track=track
        )

        await asyncio.gather(
            _handle_audio_input(audio_stream),
            _handle_transcription_output(stt_forwarder),
        )

    async def _handle_audio_input(audio_stream: rtc.AudioStream):
        """Pushes buffered audio frames to the speech-to-text stream."""
        client = OpenAI(api_key=openai_api_key)
        buffer_audio = AudioSegment.silent(duration=0)  # Start with an empty buffer
        min_audio_length = 100  # Minimum duration in milliseconds (0.1s)

        async for ev in audio_stream:
            
            if ev.frame is None:
                logger.warning("Received an empty audio frame, skipping.")
                continue

            logger.info(f"Received audio frame, size: {len(ev.frame)} bytes.")
            try:
                # Convert frame to WAV bytes
                wav_bytes = ev.frame.to_wav_bytes()

                # Load into AudioSegment
                frame_audio = AudioSegment.from_wav(io.BytesIO(wav_bytes))

                # Append to buffer
                buffer_audio += frame_audio

                # Check if buffer has enough duration
                if len(buffer_audio) >= min_audio_length:
                    logger.info("Processing buffered audio for transcription...")

                    # Save to a buffer
                    wav_buffer = io.BytesIO()
                    buffer_audio.export(wav_buffer, format="wav")
                    wav_buffer.seek(0)

                    # Send to Whisper
                    response = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=wav_buffer  # Corrected API call
                    )

                    if response and hasattr(response, "text"):
                        print("Transcription:", response.text)

                    # Reset buffer after sending
                    buffer_audio = AudioSegment.silent(duration=0)

            except Exception as e:
                logger.error(f"Error during transcription: {e}")

    async def _handle_transcription_output(stt_forwarder: transcription.STTSegmentsForwarder):
        """Handles transcription output (can be modified for real-time feedback)."""
        pass

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
