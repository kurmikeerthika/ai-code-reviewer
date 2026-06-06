// frontend/src/components/upload/FileUpload.tsx

import { useState } from 'react'
import api from '../../services/api'
import { useAppStore } from '../../store/useAppStore'

export default function FileUpload() {
  const [file, setFile] = useState<File | null>(null)

  const {
    setSessionId,
    setReviewResult,
    setLoading,
    loading,
    sessionId,
    setActivePage,
  } = useAppStore()

  // UPLOAD FILE
  const handleUpload = async () => {
    if (!file) {
      alert('Please select a file')
      return
    }

    try {
      setLoading(true)

      const formData = new FormData()

      formData.append('files', file)

      const response = await api.post(
        '/api/v1/upload/',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      )

      const uploadedSessionId =
        response.data.session_id

      setSessionId(uploadedSessionId)

      alert(
        `Upload successful\nSession ID: ${uploadedSessionId}`
      )
    } catch (error) {
      console.error(error)

      alert('Upload failed')
    } finally {
      setLoading(false)
    }
  }

  // START REVIEW
  const handleReview = async () => {
    if (!sessionId) {
      alert('Please upload file first')
      return
    }

    try {
      setLoading(true)
      console.log('Starting review...')
      const response = await api.post(
        '/api/v1/review/',
        {
          session_id: sessionId,
        }
      )
      
      console.log(response.data)

      setReviewResult(response.data)

      // SAVE TO HISTORY
      const reviewItem = {
      id: Date.now(),

      type: "upload",

      filename: file?.name || "Unknown File",

      totalIssues:
        response.data?.statistics?.total_issues || 0,

      critical:
        response.data?.statistics?.severity_counts?.critical || 0,

      high:
        response.data?.statistics?.severity_counts?.high || 0,

      medium:
        response.data?.statistics?.severity_counts?.medium || 0,

      summary:
        response.data?.summary || "No summary",

      issues:response.data.issues || [],


      report: response.data,

      date: new Date().toLocaleString(),
    }

    const existingHistory = JSON.parse(
    localStorage.getItem("reviewHistory") || "[]"
    )

    existingHistory.unshift(reviewItem)

    localStorage.setItem(
      "reviewHistory",
      JSON.stringify(existingHistory)
    )

      setActivePage('review')
    } catch (error) {
      console.error(error)

      alert('Review failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
      <h2 className="text-2xl text-white font-bold mb-4">
        Upload Source Code
      </h2>

      <input
        type="file"
        onChange={(e) => {
          if (
            e.target.files &&
            e.target.files[0]
          ) {
            setFile(e.target.files[0])
          }
        }}
        className="block w-full text-zinc-300"
      />

      <div className="flex gap-4 mt-6">
        <button
          onClick={handleUpload}
          disabled={loading}
          className="px-5 py-2 rounded-xl bg-cyan-500 text-black font-semibold"
        >
          {loading ? 'Uploading...' : 'Upload'}
        </button>

        {sessionId && (
          <button
            onClick={handleReview}
            disabled={loading}
            className="px-5 py-2 rounded-xl bg-white text-black font-semibold"
          >
            Start Review
          </button>
        )}
      </div>
    </div>
  )
}