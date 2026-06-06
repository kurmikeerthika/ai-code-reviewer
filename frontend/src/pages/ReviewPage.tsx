import { useAppStore } from '../store/useAppStore'

export default function ReviewPage() {
  const { reviewResult } = useAppStore()

  const issues = reviewResult?.issues || []

  return (
    <div className="p-6 text-white">
      <h1 className="text-4xl font-bold mb-6">
        AI Review Result
      </h1>

      {issues.length === 0 ? (
        <div className="bg-zinc-900 p-6 rounded-2xl">
          No issues found
        </div>
      ) : (
        <div className="space-y-6">
          {issues.map((issue: any, index: number) => (
            <div
              key={index}
              className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6"
            >
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold">
                  {issue.title}
                </h2>

                <span className="px-3 py-1 rounded-full bg-red-500 text-black font-bold">
                  {issue.severity}
                </span>
              </div>

              <p className="mt-4 text-zinc-300">
                {issue.description}
              </p>

              <div className="mt-4">
                <p className="font-semibold">
                  File:
                </p>

                <p className="text-cyan-400">
                  {issue.filename}
                </p>
              </div>

              <div className="mt-4">
                <p className="font-semibold mb-2">
                  Code
                </p>

                <pre className="bg-black p-4 rounded-xl overflow-auto text-sm">
                  <code>
                    {issue.code_snippet}
                  </code>
                </pre>
              </div>

              <div className="mt-4">
                <p className="font-semibold mb-2">
                  Suggested Fix
                </p>

                <div className="bg-zinc-800 p-4 rounded-xl">
                  {issue.suggestion}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}