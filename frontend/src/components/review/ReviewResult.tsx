// frontend/src/components/review/ReviewResult.tsx

import { useAppStore } from '../../store/useAppStore'

export default function ReviewResult() {
  const { reviewResult } = useAppStore()

  if (!reviewResult) {
    return (
      <div className="text-zinc-400">
        No review available
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
        <h2 className="text-2xl font-bold text-white mb-4">
          AI Review Results
        </h2>

        <pre className="text-sm text-zinc-300 overflow-auto">
          {JSON.stringify(
            reviewResult,
            null,
            2
          )}
        </pre>
      </div>
    </div>
  )
}