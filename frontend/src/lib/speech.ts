/**
 * Browser speech-to-text.
 *
 * Uses the Web Speech API where the browser provides it (Chrome, Edge, Safari)
 * and reports unavailability everywhere else so the caller can fall back to
 * plain typing. No external speech service is involved.
 */

interface SpeechRecognitionAlternativeLike {
  transcript: string
}
interface SpeechRecognitionResultLike {
  0: SpeechRecognitionAlternativeLike
  isFinal: boolean
  length: number
}
interface SpeechRecognitionEventLike {
  resultIndex: number
  results: { length: number; [index: number]: SpeechRecognitionResultLike }
}
interface SpeechRecognitionLike {
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  start: () => void
  stop: () => void
  abort: () => void
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onerror: ((event: { error: string }) => void) | null
  onend: (() => void) | null
}
type SpeechRecognitionConstructor = new () => SpeechRecognitionLike

function getConstructor(): SpeechRecognitionConstructor | null {
  const w = window as unknown as {
    SpeechRecognition?: SpeechRecognitionConstructor
    webkitSpeechRecognition?: SpeechRecognitionConstructor
  }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

export function isSpeechSupported(): boolean {
  return getConstructor() !== null
}

/** Maps our locale codes onto BCP-47 tags the recogniser understands. */
const SPEECH_LOCALES: Record<string, string> = {
  en: 'en-IN',
  hi: 'hi-IN',
  ta: 'ta-IN',
  te: 'te-IN',
}

export interface DictationHandlers {
  onTranscript: (text: string, isFinal: boolean) => void
  onError: (message: string) => void
  onEnd: () => void
}

export interface DictationSession {
  stop: () => void
}

export function startDictation(
  locale: string,
  handlers: DictationHandlers,
): DictationSession | null {
  const Recognition = getConstructor()
  if (!Recognition) return null

  const recognition = new Recognition()
  recognition.lang = SPEECH_LOCALES[locale] ?? 'en-IN'
  recognition.continuous = true
  recognition.interimResults = true
  recognition.maxAlternatives = 1

  recognition.onresult = (event) => {
    let interim = ''
    let final = ''
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const result = event.results[i]
      const text = result[0]?.transcript ?? ''
      if (result.isFinal) final += text
      else interim += text
    }
    if (final) handlers.onTranscript(final.trim(), true)
    else if (interim) handlers.onTranscript(interim.trim(), false)
  }

  recognition.onerror = (event) => {
    const messages: Record<string, string> = {
      'not-allowed': 'Microphone access was blocked. Allow it, or type your request instead.',
      'service-not-allowed': 'Speech recognition is not permitted here. Please type instead.',
      'no-speech': 'No speech was detected. Try again, or type your request.',
      network: 'Speech recognition needs a network connection. Please type instead.',
      aborted: '',
    }
    const message = messages[event.error] ?? 'Voice input stopped unexpectedly. Please type instead.'
    if (message) handlers.onError(message)
  }

  recognition.onend = () => handlers.onEnd()

  try {
    recognition.start()
  } catch {
    handlers.onError('Voice input could not start. Please type your request.')
    return null
  }

  return {
    stop: () => {
      try {
        recognition.stop()
      } catch {
        /* already stopped */
      }
    },
  }
}
