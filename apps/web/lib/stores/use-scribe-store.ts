import { create } from "zustand"

export interface TranscriptSegment {
  text: string
  isMedicallyRelevant: boolean
  speakerLabel: string | null
  sequence: number
  timestampStartMs: number
  timestampEndMs: number
}

export interface SOAPNote {
  subjective: string
  objective: string
  assessment: string
  plan: string
}

type ScribeStatus =
  | "idle"
  | "connecting"
  | "ready"
  | "recording"
  | "processing"
  | "completed"
  | "error"

interface ScribeState {
  consultationId: string | null
  status: ScribeStatus
  transcriptSegments: TranscriptSegment[]
  soapNote: SOAPNote
  isRecording: boolean
  elapsedMs: number
  language: string
  errorMessage: string | null

  setConsultationId: (id: string | null) => void
  setStatus: (status: ScribeStatus) => void
  addTranscriptSegment: (segment: TranscriptSegment) => void
  updateSOAPSection: (
    section: keyof SOAPNote,
    content: string,
  ) => void
  setLanguage: (lang: string) => void
  setElapsedMs: (ms: number) => void
  setError: (message: string | null) => void
  reset: () => void
}

const initialSOAP: SOAPNote = {
  subjective: "",
  objective: "",
  assessment: "",
  plan: "",
}

export const useScribeStore = create<ScribeState>()((set) => ({
  consultationId: null,
  status: "idle",
  transcriptSegments: [],
  soapNote: { ...initialSOAP },
  isRecording: false,
  elapsedMs: 0,
  language: "vi",
  errorMessage: null,

  setConsultationId: (id) => set({ consultationId: id }),
  setStatus: (status) =>
    set({
      status,
      isRecording: status === "recording",
      errorMessage: status === "error" ? undefined : null,
    }),
  addTranscriptSegment: (segment) =>
    set((state) => ({
      transcriptSegments: [...state.transcriptSegments, segment],
    })),
  updateSOAPSection: (section, content) =>
    set((state) => ({
      soapNote: { ...state.soapNote, [section]: content },
    })),
  setLanguage: (language) => set({ language }),
  setElapsedMs: (elapsedMs) => set({ elapsedMs }),
  setError: (errorMessage) =>
    set({ errorMessage, status: errorMessage ? "error" : "idle" }),
  reset: () =>
    set({
      consultationId: null,
      status: "idle",
      transcriptSegments: [],
      soapNote: { ...initialSOAP },
      isRecording: false,
      elapsedMs: 0,
      errorMessage: null,
    }),
}))
