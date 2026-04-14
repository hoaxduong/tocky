class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this._paused = false
    this.port.onmessage = (event) => {
      if (event.data.type === "pause") this._paused = true
      else if (event.data.type === "resume") this._paused = false
    }
  }

  process(inputs) {
    if (this._paused) return true

    const input = inputs[0]
    if (!input || !input[0] || input[0].length === 0) return true

    // Send a copy of the audio data to the main thread
    this.port.postMessage(
      { type: "audio", samples: input[0].slice() },
      [input[0].buffer],
    )
    return true
  }
}

registerProcessor("pcm-processor", PCMProcessor)
