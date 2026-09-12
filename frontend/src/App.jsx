import { useRef, useState } from 'react'
import './App.css'

const API_URL = 'https://bundle-haggler-sneezing.ngrok-free.dev'

function App() {
  const [transcript, setTranscript] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [audioBlob, setAudioBlob] = useState(null)
  const mediaRecorderRef = useRef(null)

  const toggleRecording = async () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop()
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      })

      const recorder = new MediaRecorder(stream)
      const chunks = []

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data)
        }
      }

      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'audio/webm' })
        setAudioBlob(blob)
        stream.getTracks().forEach((track) => track.stop())
        setIsRecording(false)
      }

      mediaRecorderRef.current = recorder
      recorder.start()
      setIsRecording(true)
      setError('')
    } catch (err) {
      setError(
        'Could not access your microphone. Please allow microphone access.'
      )
    }
  }

  const processTranscript = async () => {
    if (!transcript.trim()) {
      setError('Please enter a Swahili voice transcript.')
      return
    }

    setLoading(true)
    setError('')
    setResult(null)

    try {
      const response = await fetch(`${API_URL}/process`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          transcript: transcript,
          model: 'logistic_regression',
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Something went wrong.')
      }

      setResult(data)
    } catch (err) {
      setError(
        `Could not connect to the Speech-to-USSD API. ${err.message}`
      )
    } finally {
      setLoading(false)
    }
  }

  const processAudio = async () => {
    if (!audioBlob) {
      setError('Please record your voice first.')
      return
    }

    setLoading(true)
    setError('')
    setResult(null)

    try {
      const formData = new FormData()

      formData.append(
        'file',
        audioBlob,
        'recording.webm'
      )

      formData.append(
        'model',
        'logistic_regression'
      )

      const response = await fetch(`${API_URL}/process-audio`, {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Something went wrong.')
      }

      setResult(data)

      if (data.transcript) {
        setTranscript(data.transcript)
      }
    } catch (err) {
      setError(
        `Could not process the recorded audio. ${err.message}`
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div className="logo">
          <span className="logo-icon">🎙️</span>

          <div>
            <h1>Speech-to-USSD</h1>
            <p>Swahili Voice Assistant</p>
          </div>
        </div>

        <div className="status">
          <span className="status-dot"></span>
          API Connected
        </div>
      </header>

      <main className="container">

        <section className="hero">
          <p className="eyebrow">
            VOICE • INTENT • USSD
          </p>

          <h2>
            Turn your voice into USSD commands
          </h2>

          <p>
            Record a Swahili voice command or enter a
            transcript below and let the system understand
            your request and generate the appropriate USSD
            sequence.
          </p>
        </section>

        <section className="card input-card">

          <div className="card-header">
            <div>
              <h3>Voice Input</h3>

              <p>
                Record what the user says in Swahili or
                enter the transcript manually.
              </p>
            </div>

            <span className="language-badge">
              SW
            </span>
          </div>

          <div className="recording-controls">

            <button
              className="process-button"
              onClick={toggleRecording}
              disabled={loading}
            >
              {isRecording
                ? '⏹️ Stop Recording'
                : '🎙️ Start Recording'}
            </button>

            {audioBlob && !isRecording && (
              <button
                className="process-button"
                onClick={processAudio}
                disabled={loading}
              >
                {loading
                  ? 'Processing...'
                  : '⚡ Process Voice'}
              </button>
            )}

          </div>

          {isRecording && (
            <p className="recording-status">
              🔴 Recording... Speak your Swahili command.
            </p>
          )}

          <textarea
            value={transcript}
            onChange={(e) =>
              setTranscript(e.target.value)
            }
            placeholder="Mfano: Nataka kutuma shilingi elfu tano kwa John"
            rows="5"
          />

          <button
            className="process-button"
            onClick={processTranscript}
            disabled={loading || isRecording}
          >
            {loading
              ? 'Processing...'
              : '⚡ Process Transcript'}
          </button>

          {error && (
            <div className="error">
              {error}
            </div>
          )}

        </section>

        {result && (
          <section className="results">

            <div className="card">

              <div className="card-header">
                <div>
                  <h3>Processing Result</h3>

                  <p>
                    What the Speech-to-USSD pipeline
                    understood.
                  </p>
                </div>
              </div>

              <div className="result-grid">

                <div className="result-item">
                  <span>Transcript</span>

                  <strong>
                    {result.transcript}
                  </strong>
                </div>

                <div className="result-item">
                  <span>Normalized Text</span>

                  <strong>
                    {result.normalized_text}
                  </strong>
                </div>

                <div className="result-item">
                  <span>Intent</span>

                  <strong className="intent">
                    {result.intent}
                  </strong>
                </div>

                <div className="result-item">
                  <span>Confidence</span>

                  <strong>
                    {(result.confidence * 100).toFixed(2)}%
                  </strong>
                </div>

              </div>
            </div>

            <div className="card ussd-card">

              <div className="card-header">

                <div>
                  <h3>USSD Response</h3>

                  <p>
                    Generated USSD menu and sequence.
                  </p>
                </div>

                <span className="ussd-icon">
                  📱
                </span>

              </div>

              <div className="ussd-menu">

                {result.ussd_menu && (
                  <div className="menu-title">
                    {result.ussd_menu}
                  </div>
                )}

                <div className="ussd-code">
                  {result.ussd}
                </div>

              </div>

            </div>

            <div className="card">

              <div className="card-header">

                <div>
                  <h3>Extracted Information</h3>

                  <p>
                    Important details detected from
                    the request.
                  </p>
                </div>

              </div>

              <div className="slots">

                {Object.entries(
                  result.slots || {}
                ).length > 0 ? (

                  Object.entries(
                    result.slots
                  ).map(([key, value]) => (

                    <div
                      className="slot"
                      key={key}
                    >
                      <span>{key}</span>

                      <strong>
                        {String(value)}
                      </strong>
                    </div>

                  ))

                ) : (

                  <p className="empty">
                    No slots detected.
                  </p>

                )}

              </div>

            </div>

          </section>
        )}

      </main>

      <footer>
        <p>
          Speech-to-USSD • Capstone Project
        </p>
      </footer>

    </div>
  )
}

export default App

