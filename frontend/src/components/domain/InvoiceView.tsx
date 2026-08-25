/**
 * Invoice.
 *
 * Rendered in a modal, printable, and downloadable as a plain text document
 * built in the browser. Clearly stamped as a simulated demo invoice.
 */

import { Download, Printer, X } from 'lucide-react'
import { useEffect, useRef } from 'react'

import { currency, formatDateTime } from '../../lib/format'
import type { Invoice } from '../../lib/types'
import { Badge, Button, cx } from '../ui'

function toPlainText(invoice: Invoice): string {
  const line = '-'.repeat(58)
  const rows = invoice.lines
    .map((item) => `${item.description}\n${' '.repeat(38)}${currency(item.amount)}`)
    .join('\n')
  const distribution = invoice.distribution
    .map((item) => `  ${item.label.padEnd(30)}${currency(item.amount)}`)
    .join('\n')

  return [
    invoice.cooperative.name,
    `${invoice.cooperative.city}, ${invoice.cooperative.state}  (${invoice.cooperative.code})`,
    line,
    'SIMULATED DEMO INVOICE - NO REAL TRANSACTION TOOK PLACE',
    line,
    `Invoice      : ${invoice.invoice_number}`,
    `Issued       : ${formatDateTime(invoice.issued_at)}`,
    `Booking      : ${invoice.booking.reference}`,
    `Service      : ${invoice.booking.service}`,
    `Worker       : ${invoice.worker.name ?? '-'}`,
    '',
    `Billed to    : ${invoice.customer.name}`,
    `               ${invoice.customer.address}`,
    line,
    rows,
    line,
    `TOTAL        ${' '.repeat(25)}${currency(invoice.total)}`,
    `Method       : ${invoice.method}`,
    `Status       : ${invoice.status}`,
    '',
    'Cooperative distribution',
    distribution,
    line,
    'Thank you for supporting your local labour cooperative.',
    '',
  ].join('\n')
}

export function InvoiceModal({
  invoice,
  onClose,
}: {
  invoice: Invoice
  onClose: () => void
}) {
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    closeRef.current?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const download = () => {
    const blob = new Blob([toPlainText(invoice)], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${invoice.invoice_number}.txt`
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-ink-900/40 p-0 backdrop-blur-[2px] sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-label={`Invoice ${invoice.invoice_number}`}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div className="animate-fade-up max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-white shadow-[var(--shadow-overlay)] sm:rounded-2xl">
        <header className="border-ink-200 sticky top-0 flex items-center justify-between gap-3 border-b bg-white px-5 py-3.5">
          <div>
            <h2 className="text-ink-900 text-base font-semibold">Invoice</h2>
            <p className="text-ink-500 font-mono text-xs">{invoice.invoice_number}</p>
          </div>
          <div className="no-print flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => window.print()} icon={<Printer className="size-4" aria-hidden />}>
              Print
            </Button>
            <Button variant="secondary" size="sm" onClick={download} icon={<Download className="size-4" aria-hidden />}>
              Download
            </Button>
            <button
              ref={closeRef}
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="text-ink-500 hover:bg-ink-100 hover:text-ink-800 rounded-lg p-1.5"
            >
              <X className="size-4" aria-hidden />
            </button>
          </div>
        </header>

        <div className="space-y-5 px-5 py-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-ink-900 font-semibold">{invoice.cooperative.name}</p>
              <p className="text-ink-500 text-sm">
                {invoice.cooperative.city}, {invoice.cooperative.state}
              </p>
              <p className="text-ink-400 font-mono text-xs">{invoice.cooperative.code}</p>
            </div>
            <Badge tone="warn">{invoice.simulated ? 'Simulated' : invoice.status}</Badge>
          </div>

          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <div>
              <dt className="text-ink-500 text-xs">Issued</dt>
              <dd className="text-ink-900">{formatDateTime(invoice.issued_at)}</dd>
            </div>
            <div>
              <dt className="text-ink-500 text-xs">Booking</dt>
              <dd className="text-ink-900 font-mono">{invoice.booking.reference}</dd>
            </div>
            <div>
              <dt className="text-ink-500 text-xs">Billed to</dt>
              <dd className="text-ink-900">{invoice.customer.name}</dd>
            </div>
            <div>
              <dt className="text-ink-500 text-xs">Worker</dt>
              <dd className="text-ink-900">{invoice.worker.name ?? '-'}</dd>
            </div>
          </dl>

          <div className="border-ink-200 overflow-hidden rounded-xl border">
            <table>
              <thead className="bg-ink-50">
                <tr>
                  <th className="text-ink-500 px-3 py-2 text-left text-xs font-semibold uppercase">
                    Description
                  </th>
                  <th className="text-ink-500 px-3 py-2 text-right text-xs font-semibold uppercase">
                    Amount
                  </th>
                </tr>
              </thead>
              <tbody>
                {invoice.lines.map((item) => (
                  <tr key={item.description} className="border-ink-100 border-t">
                    <td className="text-ink-700 px-3 py-2.5 text-sm">{item.description}</td>
                    <td className="text-ink-900 px-3 py-2.5 text-right text-sm font-medium tabular-nums">
                      {currency(item.amount)}
                    </td>
                  </tr>
                ))}
                <tr className="border-ink-200 bg-ink-50 border-t">
                  <td className="text-ink-900 px-3 py-2.5 text-sm font-semibold">Total</td>
                  <td className="text-ink-900 px-3 py-2.5 text-right text-base font-semibold tabular-nums">
                    {currency(invoice.total)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div>
            <p className="text-ink-500 mb-2 text-xs font-semibold tracking-wide uppercase">
              Cooperative distribution
            </p>
            <dl className="divide-ink-100 divide-y">
              {invoice.distribution.map((item) => (
                <div key={item.label} className="flex justify-between py-1.5 text-sm">
                  <dt className="text-ink-600">{item.label}</dt>
                  <dd className="text-ink-900 font-medium tabular-nums">
                    {currency(item.amount)}
                  </dd>
                </div>
              ))}
            </dl>
          </div>

          <p className={cx('text-ink-400 border-ink-100 border-t pt-4 text-xs')}>
            Demo cooperative payment distribution. This invoice is generated for demonstration
            purposes and records no real financial transaction.
          </p>
        </div>
      </div>
    </div>
  )
}
