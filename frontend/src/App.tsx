import Sidebar from './components/layout/Sidebar'
import Navbar from './components/layout/Navbar'

import DashboardPage from './pages/DashboardPage'
import UploadPage from './pages/UploadPage'
import GithubPage from './pages/GithubPage'
import HistoryPage from './pages/HistoryPage'
import ReviewPage from './pages/ReviewPage'

import { useAppStore } from './store/useAppStore'

const PAGE_COMPONENTS: any = {
  dashboard: DashboardPage,
  upload: UploadPage,
  github: GithubPage,
  history: HistoryPage,
  review: ReviewPage,
}

export default function App() {
  const { activePage } = useAppStore()

  const CurrentPage =
    PAGE_COMPONENTS[activePage] || DashboardPage

  return (
    <div className="flex bg-zinc-950 text-white min-h-screen">
      <Sidebar />

      <div className="flex-1 flex flex-col">
        <Navbar />

        <main className="p-6">
          <CurrentPage />
        </main>
      </div>
    </div>
  )
}