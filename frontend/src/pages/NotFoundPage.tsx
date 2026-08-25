import { Link } from 'react-router-dom'

import { homeRouteFor, useAuth } from '../auth/AuthContext'
import { BrandMark } from '../components/layout/BrandMark'
import { Button, Card } from '../components/ui'

export default function NotFoundPage() {
  const { user } = useAuth()

  return (
    <div className="bg-ink-50 flex min-h-dvh flex-col">
      <header className="border-ink-200 border-b bg-white">
        <div className="mx-auto w-full max-w-4xl px-4 py-3.5 sm:px-6">
          <BrandMark />
        </div>
      </header>
      <main className="mx-auto flex w-full max-w-md flex-1 items-center px-4 py-10">
        <Card className="w-full space-y-4 text-center">
          <p className="text-brand-700 text-4xl font-semibold">404</p>
          <div>
            <h1 className="text-lg font-semibold">This page does not exist</h1>
            <p className="text-ink-500 mt-1 text-sm">
              The link may be out of date, or the page may have moved.
            </p>
          </div>
          <Link to={user ? homeRouteFor(user.role) : '/'}>
            <Button block>{user ? 'Back to your dashboard' : 'Back to the home page'}</Button>
          </Link>
        </Card>
      </main>
    </div>
  )
}
