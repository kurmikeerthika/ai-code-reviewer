import { useEffect, useState } from "react";

export default function DashboardPage() {
  const [stats, setStats] = useState({
    totalReviews: 0,
    totalIssues: 0,
    uploadReviews: 0,
    githubReviews: 0,
  });

  useEffect(() => {
    const history = JSON.parse(
      localStorage.getItem("reviewHistory") || "[]"
    );

    const totalReviews = history.length;

    const totalIssues = history.reduce(
      (sum: number, item: any) =>
        sum + (item.totalIssues || 0),
      0
    );

    const uploadReviews = history.filter(
      (item: any) => item.type === "upload"
    ).length;

    const githubReviews = history.filter(
      (item: any) => item.type === "github"
    ).length;

    setStats({
      totalReviews,
      totalIssues,
      uploadReviews,
      githubReviews,
    });
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-5xl font-bold text-white">
        Dashboard
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">

        <div className="bg-zinc-900 p-6 rounded-2xl">
          <p>Total Reviews</p>
          <h2 className="text-5xl font-bold text-cyan-400">
            {stats.totalReviews}
          </h2>
        </div>

        <div className="bg-zinc-900 p-6 rounded-2xl">
          <p>Total Issues</p>
          <h2 className="text-5xl font-bold text-red-400">
            {stats.totalIssues}
          </h2>
        </div>

        <div className="bg-zinc-900 p-6 rounded-2xl">
          <p>Upload Reviews</p>
          <h2 className="text-5xl font-bold text-green-400">
            {stats.uploadReviews}
          </h2>
        </div>

        <div className="bg-zinc-900 p-6 rounded-2xl">
          <p>GitHub Reviews</p>
          <h2 className="text-5xl font-bold text-yellow-400">
            {stats.githubReviews}
          </h2>
        </div>

      </div>
    </div>
  );
}