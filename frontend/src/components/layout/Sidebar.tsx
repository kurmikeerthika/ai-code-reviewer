import {
  LayoutDashboard,
  Upload,
  GitBranch,
  History,
} from 'lucide-react'

import { useAppStore } from '../../store/useAppStore'

const items = [
  {
    icon: LayoutDashboard,
    label: 'dashboard',
  },
  {
    icon: Upload,
    label: 'upload',
  },
  {
    icon: GitBranch,
    label: 'github',
  },
  {
    icon: History,
    label: 'history',
  },
]

export default function Sidebar() {
  const { activePage, setActivePage } =
    useAppStore()

  return (
    <aside className="w-64 bg-zinc-900 border-r border-zinc-800 min-h-screen p-4">
      <h1 className="text-2xl font-bold text-cyan-400 mb-8">
        AI Reviewer
      </h1>

      <div className="space-y-3">
        {items.map((item) => {
          const Icon = item.icon

          return (
            <button
              key={item.label}
              onClick={() =>
                setActivePage(item.label as any)
              }
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${
                activePage === item.label
                  ? 'bg-cyan-500 text-black'
                  : 'bg-zinc-800 hover:bg-zinc-700'
              }`}
            >
              <Icon size={20} />

              <span className="capitalize">
                {item.label}
              </span>
            </button>
          )
        })}
      </div>
    </aside>
  )
}