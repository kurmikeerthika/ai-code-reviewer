// frontend/src/pages/HistoryPage.tsx

import { useEffect, useState } from "react";
import { useAppStore } from "../store/useAppStore"

export default function HistoryPage() {
  const { setActivePage, setReviewResult } = useAppStore()
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    const storedHistory = JSON.parse(
      localStorage.getItem("reviewHistory") || "[]"
    );

    setHistory(storedHistory);
  }, []);

  return (
    <div className="p-6 text-white">
      <h1 className="text-4xl font-bold mb-6">
        History
      </h1>

      {history.length === 0 ? (
        <div className="bg-zinc-900 p-6 rounded-2xl">
          No reviews yet
        </div>
      ) : (
        <div className="space-y-4">
          {history.map((item) => (
            <div
              key={item.id}
              className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6"
            >
              <div className="flex justify-between mb-4">
                <h2 className="text-2xl font-bold text-cyan-400">
                  
                  {item.type==="upload" 
                  ? item.filename 
                  : item.repo}
                </h2>

                <span className="px-2 py-1 rounded bg-cyan-500 text-black text-xs">
                  {item.type === "upload" ? "UPLOAD" : "GITHUB"}
                </span>
                  

                {item.type === "upload" ? (
                   <p className="text-zinc-400">
                    Upload Review
                   </p>
                ) : (
                  <p className="text-zinc-400">
                    PR #{item.pr}
                    </p>
                  )}
   
                <span className="text-zinc-400">
                  {item.date}
                </span>
              </div>

              {item.type !== "upload" && (
                 <p className="mb-2">
                  <strong>PR:</strong> #{item.pr}
                </p>

              )}

              <p className="mb-2">
                <strong>Total Issues:</strong> {item.totalIssues}
              </p>

              <p className="mb-2 text-red-400">
                Critical: {item.critical}
              </p>

              <p className="mb-2 text-orange-400">
                High: {item.high}
              </p>

              <p className="mb-2 text-yellow-400">
                Medium: {item.medium}
              </p>

              <div className="mt-4 bg-zinc-800 p-4 rounded-xl">
                {item.summary}
              </div>
              <button
              onClick={() => {
                setReviewResult (
                  item.report || {
                    issues: item.issues || [],
                    summary:item.summary,
                    statistics:{
                      total_issues: item.totalIssues,
                    },
                  }
                )
                setActivePage("review")
              }}
              
              className="mt-4 px-4 py-2 bg-cyan-500 text-black rounded-lg font-semibold"
              >
                View Details
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}