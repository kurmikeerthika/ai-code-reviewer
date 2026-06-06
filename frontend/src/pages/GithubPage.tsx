// frontend/src/pages/GithubPage.tsx

import { useState } from 'react'

export default function GithubPage() {
  const [prUrl, setPrUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')

  const handleReview = async () => {
    if (!prUrl) {
      alert('Please enter PR URL')
      return
    }

    try {
      setLoading(true)

      const response = await fetch(
       'http://localhost:8000/api/v1/github/review-pr',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            pr_url: prUrl,
            post_comment: false,
            max_files: 10,
          }),
        }
      )

      const data = await response.json()

      if (!response.ok) {
        // alert(data.detail || "Review Failed")
         setError(data.detail || "Review Failed")
        return
      }


      // console.log(data)
      console.log("FULL RESPONSE:", data)

      setError('')

      setResult(data)


      const reviewItem = {
        id: Date.now(),
        type:"github",

        repo:
        prUrl.split("/")[4] ||
        "Unknown Repo",
        
        pr:
        data.pr_metadata?.pr_number ||
        "Unknown PR",

        totalIssues:
        data.report?.statistics?.total_issues || 0,

        critical:
        data.report?.statistics?.severity_counts?.critical || 0,

        high:
        data.report?.statistics?.severity_counts?.high || 0,

        medium:
        data.report?.statistics?.severity_counts?.medium || 0,

        date: new Date().toLocaleString(),

        summary:
        data.report?.summary || "No summary",
      };

    const existingHistory = JSON.parse(
    localStorage.getItem("reviewHistory") || "[]"
    );

    existingHistory.unshift(reviewItem);

    localStorage.setItem(
      "reviewHistory",
       JSON.stringify(existingHistory)
    );

    } catch (error) {
      console.error(error)
      alert('PR Review Failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 text-white">
      <h1 className="text-4xl font-bold mb-6">
        GitHub PR Review
      </h1>

      {/* INPUT */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-6">
        <input
          type="text"
          value={prUrl}
          onChange={(e) => setPrUrl(e.target.value)}
          placeholder="Paste GitHub PR URL"
          className="w-full bg-zinc-800 text-white p-4 rounded-xl outline-none"
        />

        <button
          onClick={handleReview}
          disabled={loading}
          className="mt-4 px-6 py-3 rounded-xl bg-cyan-500 text-black font-bold"
        >
          {loading ? 'Reviewing PR...' : 'Review PR'}
        </button>
      </div>


      {error && (
        <div className="bg-red-900 border border-red-500 text-white p-4 rounded-xl mb-6">
        {error}
        </div>
      )}

      {/* RESULT */}
      {result && (
        <div className="space-y-6">

          {/* PR INFO */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
            <h2 className="text-2xl font-bold mb-4">
              PR Information
            </h2>

            <p>
              <span className="font-bold">Title:</span>{' '}
              {result.pr_metadata?.title}
            </p>

            <p>
              <span className="font-bold">Author:</span>{' '}
              {result.pr_metadata?.author}
            </p>

            <p>
              <span className="font-bold">Repository:</span>{' '}
              {result.pr_metadata?.repo}
            </p>
          </div>

          {/* SUMMARY */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
            <h2 className="text-2xl font-bold mb-4">
              AI Summary
            </h2>

            <p className="text-zinc-300 whitespace-pre-wrap">
              {result.report?.summary}
            </p>
          </div>
          {/* <pre className="text-white text-xs overflow-auto">
            {JSON.stringify(result, null, 2)}
          </pre> */}
          {/* STATS */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">

            <div className="bg-zinc-900 p-6 rounded-2xl">
              <p className="text-zinc-400">Total Issues</p>
              <h3 className="text-4xl font-bold text-cyan-400">
                {result.report?.statistics?.total_issues || 0}
              </h3>
            </div>

            <div className="bg-zinc-900 p-6 rounded-2xl">
              <p className="text-zinc-400">Critical</p>
              <h3 className="text-4xl font-bold text-red-500">
                {
                  result.report?.statistics?.severity_counts?.critical || 0
                }
              </h3>
            </div>

            <div className="bg-zinc-900 p-6 rounded-2xl">
              <p className="text-zinc-400">High</p>
              <h3 className="text-4xl font-bold text-orange-400">
                {
                  result.report?.statistics?.severity_counts?.high || 0
                }
              </h3>
            </div>

            <div className="bg-zinc-900 p-6 rounded-2xl">
              <p className="text-zinc-400">Medium</p>
              <h3 className="text-4xl font-bold text-yellow-400">
                {
                  result.report?.statistics?.severity_counts?.medium || 0
                }
              </h3>
            </div>

          </div>

          {/* ISSUES */}
          <div className="space-y-6">
            <h2 className="text-3xl font-bold">
              Detected Issues
            </h2>

            {result.report?.issues?.map(
              (issue: any, index: number) => (
                <div
                  key={index}
                  className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6"
                >
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-2xl font-bold">
                      {issue.title}
                    </h3>

                    <span className="px-4 py-1 rounded-full bg-red-500 text-white text-sm">
                      {issue.severity}
                    </span>
                  </div>

                  <p className="text-zinc-300 mb-4">
                    {issue.description}
                  </p>

                  <div className="mb-4">
                    <p className="font-bold mb-2">
                      File:
                    </p>

                    <p className="text-cyan-400">
                      {issue.filename}
                    </p>
                  </div>

                  <div className="mb-4">
                    <p className="font-bold mb-2">
                      Code:
                    </p>

                    <pre className="bg-black p-4 rounded-xl overflow-auto text-sm">
                      {issue.code_snippet}
                    </pre>
                  </div>

                  <div>
                    <p className="font-bold mb-2">
                      Suggested Fix:
                    </p>

                    <div className="bg-zinc-800 p-4 rounded-xl">
                      {issue.suggestion}
                    </div>
                  </div>
                </div>
              )
            )}
          </div>
        </div>
      )}
    </div>
  )
}