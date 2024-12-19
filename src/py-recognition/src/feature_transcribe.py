import sys
import audioop
import wave
import glob
import numpy

import src.microphone
import src.recognition
import src.val as val
from src import Enviroment, Logger
from src.cancellation import CancellationObject

def run(
    path:str,
    recognition_model:src.recognition.RecognitionModel,
    env:Enviroment,
    logger:Logger,
    feature:str) -> None:

    logger.print(f"path,rate,width,channels,transcribe")
    for file in glob.glob(path):
        buffer = f"\"{file}\"," 
        try:
            wf = wave.open(file, "rb")
            buffer += f"{wf.getframerate()},"
            buffer += f"{wf.getsampwidth()},"
            buffer += f"{wf.getnchannels()},"

            d = wf.readframes(-1)
            #if recognition_model.required_sample_rate is not None:
            d, _ = audioop.ratecv(
                d,
                2, # sample_width
                1,
                wf.getframerate(),
                16000,
                None)
            ret = recognition_model.transcribe(numpy.frombuffer(d, dtype=numpy.int16).flatten())
            logger.print(buffer, end="")
            logger.print(f"\"{ret.transcribe}\"")
        except wave.Error as e:
            logger.print(buffer, file=sys.stderr)
            logger.print("!!!wave.Error!!!", console=val.Console.Yellow, reset_console=True, file=sys.stderr)
            logger.print(e, console=val.Console.Yellow, reset_console=True, file=sys.stderr)
        except src.recognition.TranscribeException as e:
            logger.print(buffer, file=sys.stderr)
            logger.print("!!!TranscribeException!!!", console=val.Console.Yellow, reset_console=True, file=sys.stderr)
            logger.print(e, console=val.Console.Yellow, reset_console=True, file=sys.stderr)
        except Exception as e:
            logger.print(buffer, file=sys.stderr)
            logger.print("!!!Unhandled Exception!!!", console=val.Console.Red, reset_console=True, file=sys.stderr)
            logger.print(e, console=val.Console.Red, reset_console=True, file=sys.stderr)

