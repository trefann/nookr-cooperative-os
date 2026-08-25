/**
 * Chart wrappers.
 *
 * Recharts everywhere, configured once here: one palette, one grid treatment,
 * one tooltip. Screens pass data, never chart chrome.
 */

import type { ReactNode } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { cx } from '../ui'

/** Categorical palette: distinguishable, and calm enough for a dense screen. */
export const CHART_COLORS = [
  '#1e4d8c',
  '#2a9469',
  '#4a7fc4',
  '#c2790d',
  '#7ba5da',
  '#1a5f45',
  '#c8433d',
  '#6b7488',
] as const

export const AXIS_STYLE = {
  fontSize: 12,
  fill: '#6b7488',
} as const

const GRID_COLOR = '#e0e4ea'

interface TooltipEntry {
  name?: string | number
  value?: string | number
  color?: string
  dataKey?: string | number
}

function ChartTooltip({
  active,
  payload,
  label,
  formatter,
}: {
  active?: boolean
  payload?: TooltipEntry[]
  label?: string | number
  formatter?: (value: number, name: string) => string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="border-ink-200 rounded-lg border bg-white px-3 py-2 shadow-[var(--shadow-overlay)]">
      {label !== undefined ? (
        <p className="text-ink-900 mb-1 text-xs font-semibold">{label}</p>
      ) : null}
      <ul className="space-y-0.5">
        {payload.map((entry, index) => (
          <li key={index} className="flex items-center gap-2 text-xs">
            <span
              className="size-2 shrink-0 rounded-full"
              style={{ backgroundColor: entry.color }}
              aria-hidden
            />
            <span className="text-ink-600">{entry.name}</span>
            <span className="text-ink-900 ml-auto font-medium tabular-nums">
              {formatter && typeof entry.value === 'number'
                ? formatter(entry.value, String(entry.name ?? ''))
                : entry.value}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function ChartFrame({
  height = 260,
  children,
  className,
}: {
  height?: number
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cx('w-full', className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        {children as never}
      </ResponsiveContainer>
    </div>
  )
}

/* -------------------------------------------------------------------------- */

export interface SeriesKey {
  key: string
  label: string
  color?: string
}

export function BarSeriesChart<T extends Record<string, unknown>>({
  data,
  xKey,
  series,
  height = 260,
  horizontal = false,
  valueFormatter,
  stacked = false,
}: {
  data: T[]
  xKey: string
  series: SeriesKey[]
  height?: number
  horizontal?: boolean
  valueFormatter?: (value: number, name: string) => string
  stacked?: boolean
}) {
  return (
    <ChartFrame height={height}>
      <BarChart
        data={data}
        layout={horizontal ? 'vertical' : 'horizontal'}
        margin={{ top: 8, right: 12, bottom: 4, left: horizontal ? 8 : -18 }}
        barCategoryGap={horizontal ? '22%' : '28%'}
      >
        <CartesianGrid
          stroke={GRID_COLOR}
          strokeDasharray="3 3"
          vertical={horizontal}
          horizontal={!horizontal}
        />
        {horizontal ? (
          <>
            <XAxis type="number" tick={AXIS_STYLE} axisLine={false} tickLine={false} />
            <YAxis
              type="category"
              dataKey={xKey}
              tick={AXIS_STYLE}
              axisLine={false}
              tickLine={false}
              width={112}
            />
          </>
        ) : (
          <>
            <XAxis dataKey={xKey} tick={AXIS_STYLE} axisLine={false} tickLine={false} />
            <YAxis tick={AXIS_STYLE} axisLine={false} tickLine={false} width={44} />
          </>
        )}
        <Tooltip
          cursor={{ fill: 'rgba(30, 77, 140, 0.06)' }}
          content={<ChartTooltip formatter={valueFormatter} />}
        />
        {series.length > 1 ? (
          <Legend
            verticalAlign="top"
            align="right"
            height={28}
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: 12, color: '#4d5566' }}
          />
        ) : null}
        {series.map((item, index) => (
          <Bar
            key={item.key}
            dataKey={item.key}
            name={item.label}
            fill={item.color ?? CHART_COLORS[index % CHART_COLORS.length]}
            radius={horizontal ? [0, 5, 5, 0] : [5, 5, 0, 0]}
            stackId={stacked ? 'a' : undefined}
            maxBarSize={horizontal ? 22 : 46}
          />
        ))}
      </BarChart>
    </ChartFrame>
  )
}

export function CategoricalBarChart<T extends Record<string, unknown>>({
  data,
  xKey,
  valueKey,
  height = 260,
  horizontal = true,
  valueFormatter,
}: {
  data: T[]
  xKey: string
  valueKey: string
  height?: number
  horizontal?: boolean
  valueFormatter?: (value: number, name: string) => string
}) {
  return (
    <ChartFrame height={height}>
      <BarChart
        data={data}
        layout={horizontal ? 'vertical' : 'horizontal'}
        margin={{ top: 8, right: 16, bottom: 4, left: horizontal ? 8 : -18 }}
      >
        <CartesianGrid
          stroke={GRID_COLOR}
          strokeDasharray="3 3"
          vertical={horizontal}
          horizontal={!horizontal}
        />
        {horizontal ? (
          <>
            <XAxis type="number" tick={AXIS_STYLE} axisLine={false} tickLine={false} />
            <YAxis
              type="category"
              dataKey={xKey}
              tick={AXIS_STYLE}
              axisLine={false}
              tickLine={false}
              width={124}
            />
          </>
        ) : (
          <>
            <XAxis dataKey={xKey} tick={AXIS_STYLE} axisLine={false} tickLine={false} />
            <YAxis tick={AXIS_STYLE} axisLine={false} tickLine={false} width={44} />
          </>
        )}
        <Tooltip
          cursor={{ fill: 'rgba(30, 77, 140, 0.06)' }}
          content={<ChartTooltip formatter={valueFormatter} />}
        />
        <Bar dataKey={valueKey} radius={horizontal ? [0, 5, 5, 0] : [5, 5, 0, 0]} maxBarSize={26}>
          {data.map((_, index) => (
            <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ChartFrame>
  )
}

export function TrendAreaChart<T extends Record<string, unknown>>({
  data,
  xKey,
  series,
  height = 240,
  valueFormatter,
}: {
  data: T[]
  xKey: string
  series: SeriesKey[]
  height?: number
  valueFormatter?: (value: number, name: string) => string
}) {
  return (
    <ChartFrame height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: -18 }}>
        <defs>
          {series.map((item, index) => (
            <linearGradient key={item.key} id={`grad-${item.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="0%"
                stopColor={item.color ?? CHART_COLORS[index % CHART_COLORS.length]}
                stopOpacity={0.28}
              />
              <stop
                offset="100%"
                stopColor={item.color ?? CHART_COLORS[index % CHART_COLORS.length]}
                stopOpacity={0.02}
              />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid stroke={GRID_COLOR} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey={xKey} tick={AXIS_STYLE} axisLine={false} tickLine={false} minTickGap={24} />
        <YAxis tick={AXIS_STYLE} axisLine={false} tickLine={false} width={44} />
        <Tooltip content={<ChartTooltip formatter={valueFormatter} />} />
        {series.length > 1 ? (
          <Legend
            verticalAlign="top"
            align="right"
            height={28}
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: 12, color: '#4d5566' }}
          />
        ) : null}
        {series.map((item, index) => (
          <Area
            key={item.key}
            type="monotone"
            dataKey={item.key}
            name={item.label}
            stroke={item.color ?? CHART_COLORS[index % CHART_COLORS.length]}
            strokeWidth={2}
            fill={`url(#grad-${item.key})`}
            dot={false}
            activeDot={{ r: 4 }}
          />
        ))}
      </AreaChart>
    </ChartFrame>
  )
}

export function TrendLineChart<T extends Record<string, unknown>>({
  data,
  xKey,
  series,
  height = 240,
  domain,
  valueFormatter,
}: {
  data: T[]
  xKey: string
  series: SeriesKey[]
  height?: number
  domain?: [number, number]
  valueFormatter?: (value: number, name: string) => string
}) {
  return (
    <ChartFrame height={height}>
      <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: -18 }}>
        <CartesianGrid stroke={GRID_COLOR} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey={xKey} tick={AXIS_STYLE} axisLine={false} tickLine={false} />
        <YAxis tick={AXIS_STYLE} axisLine={false} tickLine={false} width={44} domain={domain} />
        <Tooltip content={<ChartTooltip formatter={valueFormatter} />} />
        {series.map((item, index) => (
          <Line
            key={item.key}
            type="monotone"
            dataKey={item.key}
            name={item.label}
            stroke={item.color ?? CHART_COLORS[index % CHART_COLORS.length]}
            strokeWidth={2.25}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
            connectNulls
          />
        ))}
      </LineChart>
    </ChartFrame>
  )
}

export function DonutChart({
  data,
  height = 240,
  valueFormatter,
  centerLabel,
  centerValue,
}: {
  data: { name: string; value: number; color?: string }[]
  height?: number
  valueFormatter?: (value: number, name: string) => string
  centerLabel?: string
  centerValue?: string
}) {
  return (
    <div className="relative">
      <ChartFrame height={height}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius="58%"
            outerRadius="82%"
            paddingAngle={2}
            stroke="none"
          >
            {data.map((entry, index) => (
              <Cell key={entry.name} fill={entry.color ?? CHART_COLORS[index % CHART_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={<ChartTooltip formatter={valueFormatter} />} />
          <Legend
            verticalAlign="bottom"
            height={36}
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: 12, color: '#4d5566' }}
          />
        </PieChart>
      </ChartFrame>
      {centerValue ? (
        <div
          className="pointer-events-none absolute inset-x-0 flex flex-col items-center"
          style={{ top: height * 0.34 }}
        >
          <span className="text-ink-900 text-xl font-semibold tabular-nums">{centerValue}</span>
          {centerLabel ? <span className="text-ink-500 text-xs">{centerLabel}</span> : null}
        </div>
      ) : null}
    </div>
  )
}
