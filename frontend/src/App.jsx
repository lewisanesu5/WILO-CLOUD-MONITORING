/**
 * Predictive Maintenance Dashboard
 * Professional Industrial Monitoring Interface
 * 
 * IMPROVEMENTS:
 * - Modern industrial monitoring theme with professional styling
 * - Responsive 30/70 two-column layout (sidebar/content)
 * - Consistent card design with 14px border radius and subtle shadows
 * - Enhanced dropdown styling (48px height) with smooth transitions
 * - Improved table with sticky headers and alternating rows
 * - Professional typography hierarchy (28-36px titles, 18-22px subtitles)
 * - Better visual hierarchy and spacing
 * - Responsive design for desktop, tablet, and mobile
 * - All chart logic and API calls remain unchanged
 */

import { useEffect, useState } from 'react';
import { Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import './index.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const API_BASE_URL = 'https://wilo-cloud-monitoring.onrender.com';
const SENSORS = ['acceleration', 'current', 'audio'];
const MODES = [
  { value: 'max', label: 'MAX View' },
  { value: 'min', label: 'MIN View' },
  { value: 'combined', label: 'COMBINED View' }
];
const STAT_PARAMETERS = [
  { key: 'mean', label: 'Mean' },
  { key: 'max', label: 'Max' },
  { key: 'min', label: 'Min' },
  { key: 'std_dev', label: 'Standard Deviation' },
  { key: 'range', label: 'Range' },
  { key: 'skewness', label: 'Skewness' },
  { key: 'kurtosis', label: 'Kurtosis' },
  { key: 'frequency1', label: 'Frequency 1' },
  { key: 'frequency2', label: 'Frequency 2' },
  { key: 'frequency3', label: 'Frequency 3' },
  { key: 'frequency4', label: 'Frequency 4' },
  { key: 'frequency5', label: 'Frequency 5' },
  { key: 'amplitude1', label: 'Amplitude 1' },
  { key: 'amplitude2', label: 'Amplitude 2' },
  { key: 'amplitude3', label: 'Amplitude 3' },
  { key: 'amplitude4', label: 'Amplitude 4' },
  { key: 'amplitude5', label: 'Amplitude 5' }
];

const EVENT_TYPES = [
  {
    label: 'Motor Failures',
    options: [
      { value: 'Motor Bearing Failure', label: 'Motor Bearing Failure' },
      { value: 'Motor Overheating', label: 'Motor Overheating' },
      { value: 'Motor Winding Failure', label: 'Motor Winding Failure' },
      { value: 'Motor Shaft Misalignment', label: 'Motor Shaft Misalignment' },
      { value: 'Motor Vibration Anomaly', label: 'Motor Vibration Anomaly' },
      { value: 'Motor Stall', label: 'Motor Stall' },
      { value: 'Motor Electrical Fault', label: 'Motor Electrical Fault' }
    ]
  },
  {
    label: 'Pump Failures',
    options: [
      { value: 'Pump Seal Leakage', label: 'Pump Seal Leakage' },
      { value: 'Pump Cavitation', label: 'Pump Cavitation' },
      { value: 'Pump Impeller Damage', label: 'Pump Impeller Damage' }
    ]
  },
  {
    label: 'Other',
    options: [
      { value: '__custom__', label: 'Custom Event...' }
    ]
  }
];

// ============================================================
// REUSABLE COMPONENTS - Enhanced with Professional Styling
// ============================================================

/**
 * TimeSeriesChart Component
 * Displays raw sensor data over time
 * - Plots individual sensor readings against timestamps
 * - Shows actual time series data, not aggregated statistics
 */
function TimeSeriesChart({ sensor, sensorData, onSensorChange }) {
  // Plot raw sensor values against time
  const rawValues = sensorData?.raw_values || [];
  const rawTimestamps = sensorData?.raw_timestamps || [];

  if (!sensorData || rawValues.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-md p-8 h-full flex items-center justify-center">
        <p className="text-gray-400 text-center">No raw sensor data available</p>
      </div>
    );
  }

  const start = rawTimestamps.length ? Number(rawTimestamps[0]) : 0;
  const relativeMs = rawTimestamps.map((t) => Number(t) - start);
  const maxMs = relativeMs.length ? Math.max(...relativeMs) : 0;
  const labels = relativeMs.map((ms) => `${ms.toFixed(0)}ms`);

  const chartData = {
    labels,
    datasets: [
      {
        label: `${sensor.charAt(0).toUpperCase() + sensor.slice(1)} Sensor Readings`,
        data: rawValues,
        borderColor: '#06b6d4',
        backgroundColor: 'rgba(6, 182, 212, 0.08)',
        fill: true,
        tension: 0.3,
        pointRadius: 1,
        pointBackgroundColor: '#06b6d4',
        pointBorderColor: '#fff',
        pointBorderWidth: 1,
        pointHoverRadius: 4,
        borderWidth: 2.5
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'top', labels: { padding: 16, font: { size: 13, weight: '600' }, color: '#1f2937' } },
      tooltip: {
        backgroundColor: 'rgba(0,0,0,0.8)',
        titleFont: { size: 12 },
        bodyFont: { size: 11 },
        padding: 12,
        callbacks: {
          title: ([item]) => `Time: ${item.label}`,
          label: (item) => `${sensor}: ${item.formattedValue}`
        }
      }
    },
    scales: {
      y: {
        title: { display: true, text: `${sensor} Value`, font: { size: 12, weight: '600', color: '#374151' } },
        grid: { color: 'rgba(0,0,0,0.08)', drawBorder: false },
        ticks: { font: { size: 11, color: '#6b7280' } }
      },
      x: {
        title: { display: true, text: 'Time (s)', font: { size: 12, weight: '600', color: '#374151' } },
        grid: { display: false, drawBorder: false },
        ticks: { font: { size: 11, color: '#6b7280' }, maxRotation: 0, minRotation: 0, autoSkip: true, maxTicksLimit: 8 }
      }
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-6 flex flex-col h-full cursor-pointer" onDoubleClick={() => { /* placeholder for parent handler */ }}>
      {/* Card Header */}
      <div className="mb-6 pb-4 border-b-2 border-blue-200">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">📈 Time Series Analysis</h2>
        
        {/* Parameter Selector Dropdown */}
        <div className="w-full">
          <label className="block text-xs font-semibold text-gray-700 mb-1">Select Sensor:</label>
          <select
            value={sensor}
            onChange={(e) => onSensorChange(e.target.value)}
            className="w-40 h-10 bg-gradient-to-r from-gray-50 to-blue-50 text-gray-900 text-sm border-2 border-blue-300 rounded-lg px-3 py-2 font-medium shadow-sm hover:border-blue-500 hover:shadow-md focus:border-blue-600 focus:ring-2 focus:ring-blue-200 focus:outline-none transition duration-200 cursor-pointer"
          >
            {['acceleration', 'current', 'audio'].map(s => (
              <option key={s} value={s} className="text-gray-900">
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Chart Container */}
      <div className="relative flex-1 min-h-[380px]">
        <Line data={chartData} options={options} />
      </div>
    </div>
  );
}

// Fullscreen Modal Component
function FullscreenModal({ open, onClose, title, children }) {
  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') onClose();
    }
    if (open) window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose}></div>
      <div className="relative w-[95%] max-w-6xl max-h-[92vh] overflow-auto bg-white rounded-2xl shadow-2xl border-l-4 border-blue-600">
        <div className="flex items-center justify-between px-6 py-4 border-b-2 border-gray-200 bg-gradient-to-r from-gray-50 to-blue-50">
          <h3 className="text-lg font-bold text-gray-900">{title}</h3>
          <button onClick={onClose} className="text-gray-600 hover:text-gray-900 text-xl px-3 py-1">✕</button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

/**
 * StatisticalAnalysisChart Component
 * Displays parameter trends across 2-hour time windows
 * - Maintains original data processing and chart generation
 * - Enhanced with professional card and table styling
 */
function StatisticalAnalysisChart({ sensor, sensorData, selectedParam, historicalStats = [] }) {
  // Use historicalStats (array of file stats ordered oldest->newest) when available
  const frequencies = sensorData.frequencies || [];
  const amplitudes = sensorData.amplitudes || [];

  let paramLabel = selectedParam;

  const getParamFromEntry = (entry) => {
    if (!entry) return 0;
    if (selectedParam.startsWith('frequency')) {
      const idx = parseInt(selectedParam.replace('frequency', '')) - 1;
      return entry.frequencies?.[idx] || 0;
    }
    if (selectedParam.startsWith('amplitude')) {
      const idx = parseInt(selectedParam.replace('amplitude', '')) - 1;
      return entry.amplitudes?.[idx] || 0;
    }
    return entry.stats?.[selectedParam] || 0;
  };

  if (selectedParam.startsWith('frequency')) {
    const idx = parseInt(selectedParam.replace('frequency', '')) - 1;
    paramLabel = `Frequency ${idx + 1}`;
  } else if (selectedParam.startsWith('amplitude')) {
    const idx = parseInt(selectedParam.replace('amplitude', '')) - 1;
    paramLabel = `Amplitude ${idx + 1}`;
  }

  // If we have >=2 historical points, plot them; otherwise show informative placeholder
  const hasHistory = Array.isArray(historicalStats) && historicalStats.length >= 2;

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'top', labels: { padding: 16, font: { size: 12, weight: '600' } } }
    },
    scales: {
      y: {
        title: { display: true, text: 'Value', font: { size: 12, weight: '600' } },
        grid: { color: 'rgba(0,0,0,0.05)' }
      },
      x: {
        grid: { display: false }
      }
    }
  };

  if (!hasHistory) {
    return (
      <div className="bg-white rounded-xl shadow-md p-8 h-full flex flex-col">
        <div className="mb-6 pb-4 border-b-2 border-gray-100">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Statistical Trend Analysis</h2>
          <p className="text-sm text-gray-600 font-medium">Parameter: <span className="text-blue-600 font-semibold">{paramLabel}</span></p>
        </div>
        <div className="flex-1 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <p className="text-lg font-semibold">Insufficient historical data</p>
            <p className="text-sm mt-2">We need at least two previous uploads to build a trend.</p>
          </div>
        </div>
      </div>
    );
  }

  const labels = historicalStats.map(h => h.file_timestamp ? new Date(h.file_timestamp).toLocaleString() : '—');
  const datasetValues = historicalStats.map(h => Number(getParamFromEntry(h)));

  const chartData = {
    labels,
    datasets: [
      {
        label: `${paramLabel} - Historical`,
        data: datasetValues,
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.08)',
        fill: true,
        tension: 0.3,
        pointRadius: 6,
        pointBackgroundColor: '#10b981',
        pointBorderColor: '#fff',
        pointBorderWidth: 2
      }
    ]
  };

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden border-l-4 border-emerald-600 p-6 flex flex-col h-full hover:shadow-xl transition duration-200">
      <div className="mb-6 pb-4 border-b-2 border-emerald-200">
        <h2 className="text-xl font-bold text-gray-900 mb-3 flex items-center gap-2">📊 Statistical Trend Analysis</h2>
        <p className="text-sm text-gray-600 font-medium">Parameter: <span className="text-emerald-600 font-semibold">{paramLabel}</span></p>
      </div>
      <div className="relative flex-1 min-h-[380px]">
        <Line data={chartData} options={options} />
      </div>
    </div>
  );
}

/**
 * FileHistoryTable Component
 * Displays 10 most recent file uploads for selected sensor
 * - Enhanced with professional table styling
 * - Improved readability with better spacing
 */
function FileHistoryTable({ files, sensor }) {
  if (!files || files.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-lg overflow-hidden border-l-4 border-orange-500 hover:shadow-xl transition duration-200">
        <h3 className="text-lg font-bold text-gray-900 mb-3 px-6 pt-6 flex items-center gap-2">📄 File Upload History</h3>
        <p className="text-sm text-gray-500 text-center py-8">No files found for <span className="font-semibold text-orange-600 capitalize">{sensor}</span></p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden cursor-pointer border-l-4 border-orange-500 hover:shadow-xl transition duration-200" onDoubleClick={() => {}}>
      {/* Card Header */}
      <div className="bg-gradient-to-r from-orange-600 via-orange-500 to-amber-500 px-6 py-4 border-b-2 border-orange-400">
        <h3 className="text-lg font-bold text-white flex items-center gap-2">📜 File Upload History</h3>
        <p className="text-xs text-orange-100 mt-1">Latest 10 uploads (5 pairs)</p>
      </div>

      {/* Table Container with Scroll */}
      <div className="px-4 py-4">
        <table className="w-full">
          <tbody>
            {files.map((file, idx) => (
              <tr key={idx} className={`${idx % 2 === 0 ? 'bg-orange-50 hover:bg-orange-100' : 'bg-white hover:bg-orange-50'} transition duration-200 border-b border-gray-200 cursor-pointer`}>
                <td className="px-6 py-4 text-xs">
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gradient-to-r from-orange-400 to-orange-600 text-white text-xs font-semibold shadow-sm">
                        {idx + 1}
                      </span>
                      <span className="font-semibold text-gray-800">{file.timestamp}</span>
                    </div>
                    <div className="text-gray-600 ml-8">
                      <div className="truncate text-orange-700 font-medium">📤 {file.maxFile}</div>
                      <div className="truncate text-blue-700 font-medium">📥 {file.minFile}</div>
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function EventHistoryTable({ events, onRefresh }) {
  if (!events || events.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-lg overflow-hidden border-l-4 border-fuchsia-500 hover:shadow-xl transition duration-200">
        <div className="bg-gradient-to-r from-fuchsia-600 via-pink-600 to-rose-500 px-6 py-4 border-b-2 border-fuchsia-400 flex items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">📅 Event History</h3>
            <p className="text-xs text-fuchsia-100 mt-1">Saved failure events</p>
          </div>
          <button
            type="button"
            onClick={onRefresh}
            className="h-9 px-3 rounded-lg bg-white/15 text-white text-xs font-semibold hover:bg-white/25 transition-colors"
          >
            Refresh
          </button>
        </div>
        <p className="text-sm text-gray-500 text-center py-8 px-6">
          No events saved yet. Create one using the Event button.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden border-l-4 border-fuchsia-500 hover:shadow-xl transition duration-200">
      <div className="bg-gradient-to-r from-fuchsia-600 via-pink-600 to-rose-500 px-6 py-4 border-b-2 border-fuchsia-400 flex items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">📅 Event History</h3>
          <p className="text-xs text-fuchsia-100 mt-1">Saved failure events</p>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          className="h-9 px-3 rounded-lg bg-white/15 text-white text-xs font-semibold hover:bg-white/25 transition-colors"
        >
          Refresh
        </button>
      </div>

      <div className="max-h-[420px] overflow-y-auto p-4 space-y-3">
        {events.map((event) => (
          <div
            key={event.event_id}
            className="rounded-xl border border-fuchsia-100 bg-fuchsia-50/60 p-4 shadow-sm transition hover:bg-fuchsia-50"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-bold text-slate-900">{event.event_name}</p>
                <p className="text-xs text-slate-500 mt-1">{event.event_id}</p>
              </div>
              <span className="rounded-full bg-fuchsia-600 px-2.5 py-1 text-[11px] font-semibold text-white">
                {event.total_data_points ?? 0} pts
              </span>
            </div>

            <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
              <div>
                <span className="font-semibold text-slate-500">Created:</span>{' '}
                {event.created_at ? new Date(event.created_at).toLocaleString() : '—'}
              </div>
              <div>
                <span className="font-semibold text-slate-500">Failure time:</span>{' '}
                {event.actual_data_time_iso ? new Date(event.actual_data_time_iso).toLocaleString() : '—'}
              </div>
              <div>
                <span className="font-semibold text-slate-500">Before failure:</span>{' '}
                {typeof event.time_before_failure_seconds === 'number'
                  ? `${Math.abs(event.time_before_failure_seconds).toFixed(2)}s`
                  : '—'}
              </div>
              <div>
                <span className="font-semibold text-slate-500">Source file:</span>{' '}
                {event.source_filename || '—'}
              </div>
            </div>

            {event.description ? (
              <p className="mt-3 rounded-lg bg-white/70 px-3 py-2 text-xs text-slate-700">
                {event.description}
              </p>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function EventModal({
  open,
  onClose,
  eventName,
  customEventName,
  eventTime,
  eventDescription,
  submitting,
  onEventNameChange,
  onCustomEventNameChange,
  onEventTimeChange,
  onEventDescriptionChange,
  onSubmit
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4" onClick={onClose}>
      <div
        className="relative w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-700 transition-colors hover:bg-slate-200"
          aria-label="Close event modal"
        >
          ✕
        </button>

        <h3 className="mb-6 text-2xl font-bold text-slate-900">Create New Event</h3>

        <div className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Event Time</label>
            <input
              type="datetime-local"
              value={eventTime}
              onChange={(e) => onEventTimeChange(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2 text-slate-900 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-200"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Event Type</label>
            <select
              value={eventName}
              onChange={(e) => onEventNameChange(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2 text-slate-900 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-200"
            >
              <option value="">-- Select event type --</option>
              {EVENT_TYPES.map((group) => (
                <optgroup key={group.label} label={group.label}>
                  {group.options.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>

            {eventName === '__custom__' && (
              <input
                type="text"
                value={customEventName}
                onChange={(e) => onCustomEventNameChange(e.target.value)}
                placeholder="Enter custom event name..."
                className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-4 py-2 text-slate-900 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-200"
              />
            )}
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Description (Optional)</label>
            <textarea
              value={eventDescription}
              onChange={(e) => onEventDescriptionChange(e.target.value)}
              rows={3}
              placeholder="Enter additional details about the event..."
              className="w-full resize-none rounded-lg border border-slate-300 bg-white px-4 py-2 text-slate-900 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-200"
            />
          </div>

          <button
            type="button"
            onClick={onSubmit}
            disabled={submitting}
            className={`w-full rounded-lg bg-gradient-to-r from-purple-600 to-pink-600 px-6 py-3 font-semibold text-white shadow-lg transition hover:from-purple-700 hover:to-pink-700 ${submitting ? 'cursor-not-allowed opacity-60' : ''}`}
          >
            {submitting ? 'Creating...' : 'Create Event'}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * EnhancedStatisticsTable Component
 * Displays all sensor statistics, frequencies, and amplitudes
 * - Professional table design with sticky headers
 * - Improved readability with proper typography hierarchy
 * - All data combined in single organized table
 */
function EnhancedStatisticsTable({ sensorData, selectedSensor, mode }) {
  const parameters = [
    { key: 'mean', label: 'Mean' },
    { key: 'max', label: 'Max' },
    { key: 'min', label: 'Min' },
    { key: 'std_dev', label: 'Standard Deviation' },
    { key: 'range', label: 'Range' },
    { key: 'skewness', label: 'Skewness' },
    { key: 'kurtosis', label: 'Kurtosis' },
    { key: 'frequency1', label: 'Frequency 1 (Hz)' },
    { key: 'frequency2', label: 'Frequency 2 (Hz)' },
    { key: 'frequency3', label: 'Frequency 3 (Hz)' },
    { key: 'frequency4', label: 'Frequency 4 (Hz)' },
    { key: 'frequency5', label: 'Frequency 5 (Hz)' },
    { key: 'amplitude1', label: 'Amplitude 1' },
    { key: 'amplitude2', label: 'Amplitude 2' },
    { key: 'amplitude3', label: 'Amplitude 3' },
    { key: 'amplitude4', label: 'Amplitude 4' },
    { key: 'amplitude5', label: 'Amplitude 5' }
  ];

  const data = sensorData[selectedSensor] || {};
  const stats = data.stats || {};
  const frequencies = data.frequencies || [];
  const amplitudes = data.amplitudes || [];

  // Create combined data object (unchanged logic)
  const allData = {
    ...stats,
    frequency1: frequencies[0],
    frequency2: frequencies[1],
    frequency3: frequencies[2],
    frequency4: frequencies[3],
    frequency5: frequencies[4],
    amplitude1: amplitudes[0],
    amplitude2: amplitudes[1],
    amplitude3: amplitudes[2],
    amplitude4: amplitudes[3],
    amplitude5: amplitudes[4]
  };

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden flex flex-col h-full border-l-4 border-emerald-600 hover:shadow-xl transition duration-200">
      {/* Card Header */}
      <div className="bg-gradient-to-r from-emerald-600 via-emerald-500 to-teal-500 px-6 py-5 border-b-2 border-emerald-400">
        <h3 className="text-lg font-bold text-white mb-1 flex items-center gap-2">📊 Statistical Analysis Table</h3>
        <p className="text-xs text-emerald-100">
          Sensor: <span className="font-semibold capitalize bg-emerald-700 bg-opacity-50 px-2 py-1 rounded">{selectedSensor}</span> • 
          Mode: <span className="font-semibold uppercase bg-emerald-700 bg-opacity-50 px-2 py-1 rounded">{mode}</span>
        </p>
      </div>

      <div className="px-6 py-5">
        <table className="w-full text-sm">
          <thead className="bg-gradient-to-r from-emerald-50 to-teal-50 border-b-2 border-emerald-300">
            <tr>
              <th className="px-5 py-3 text-left font-bold text-emerald-900 whitespace-nowrap">Parameter</th>
              <th className="px-5 py-3 text-right font-bold text-emerald-900 whitespace-nowrap">Value</th>
            </tr>
          </thead>
          <tbody>
            {parameters.map((param, idx) => {
              // Group parameters visually
              const isFrequency = param.key.startsWith('frequency');
              const isAmplitude = param.key.startsWith('amplitude');
              const bgClass = isFrequency ? 'bg-blue-50 hover:bg-blue-100' : isAmplitude ? 'bg-green-50 hover:bg-green-100' : idx % 2 === 0 ? 'bg-white hover:bg-gray-50' : 'bg-gray-50 hover:bg-gray-100';
              const hoverClass = 'transition duration-200';

              return (
                <tr key={param.key} className={`${bgClass} ${hoverClass} border-b border-gray-200 cursor-pointer`}>
                  <td className="px-5 py-3 font-semibold text-gray-800 flex items-center gap-2">
                    {isFrequency && <span className="text-yellow-600 text-lg">🔊</span>}
                    {isAmplitude && <span className="text-green-600 text-lg">📊</span>}
                    {!isFrequency && !isAmplitude && <span className="text-gray-400">•</span>}
                    {param.label}
                  </td>
                  <td className="px-5 py-3 text-right font-bold text-gray-900 tabular-nums">
                    {allData[param.key] !== undefined && allData[param.key] !== null 
                      ? (typeof allData[param.key] === 'number' ? allData[param.key].toFixed(4) : allData[param.key])
                      : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}




/**
 * Main Application Component
 * Professional Industrial Monitoring Dashboard
 * 
 * Layout: 
 * - Header with title and global controls (top)
 * - Two-column responsive grid (30% sidebar / 70% content)
 * - All API calls and data logic unchanged
 */
function App() {
  // State management (unchanged)
  const [sensorData, setSensorData] = useState({});
  const [selectedSensor, setSelectedSensor] = useState('current');
  const [timeSeriesSensor, setTimeSeriesSensor] = useState('current');
  const [mode, setMode] = useState('max');
  const [selectedParam, setSelectedParam] = useState('mean');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [fileHistory, setFileHistory] = useState([]);
  const [historicalStats, setHistoricalStats] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [modalContent, setModalContent] = useState(null);
  const [eventModalOpen, setEventModalOpen] = useState(false);
  const [eventName, setEventName] = useState('');
  const [customEventName, setCustomEventName] = useState('');
  const [eventTime, setEventTime] = useState('');
  const [eventDescription, setEventDescription] = useState('');
  const [eventSubmitting, setEventSubmitting] = useState(false);
  const [events, setEvents] = useState([]);

  const openEventModal = () => {
    setEventModalOpen(true);
  };

  const closeEventModal = () => {
    setEventModalOpen(false);
    setEventName('');
    setCustomEventName('');
    setEventTime('');
    setEventDescription('');
  };

  const handleCreateEvent = async () => {
    const faultType = eventName === '__custom__' ? customEventName.trim() : eventName;

    if (!eventTime || !faultType) {
      alert('Please select a fault type and event time');
      return;
    }

    setEventSubmitting(true);

    try {
      // Call the simulate-event endpoint instead of create-event
      const response = await fetch(`${API_BASE_URL}/simulate-event`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          fault_type: faultType,
          event_time: new Date(eventTime).toISOString(),
          description: eventDescription
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to simulate event');
      }

      // Show success with sensor data preview
      alert(`✓ Event "${faultType}" simulated successfully!\n\n` +
            `Files copied: ${data.files_copied.join(', ')}\n` +
            `Database updated with sensor readings.`);
      
      // Refresh sensor data to show the simulated event
      await fetchSensorData('max');
      await fetchEvents();
      closeEventModal();
    } catch (error) {
      console.error('Error simulating event:', error);
      alert(`Error: ${error.message}`);
    } finally {
      setEventSubmitting(false);
    }
  };

  // API functions (logic unchanged - fully preserved)
  const fetchSensorData = async (selectedMode = 'max') => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/sensor-data?mode=${selectedMode}`);
      if (!response.ok) throw new Error('Failed to fetch sensor data');
      
      const result = await response.json();
      setSensorData(result.data || {});
      setLastUpdate(new Date().toLocaleTimeString());
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchFileHistory = async (sensor) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/files`);
      if (!response.ok) throw new Error('Failed to fetch files');
      
      const allFiles = await response.json();
      
      // Filter files for selected sensor
      const sensorFiles = allFiles
        .filter(f => f.name.includes(sensor))
        .sort((a, b) => new Date(b.modified) - new Date(a.modified))
        .slice(0, 10);

      // Pair max and min files with same timestamp
      const pairs = [];
      for (let i = 0; i < sensorFiles.length; i += 2) {
        if (sensorFiles[i + 1]) {
          const timestamp = new Date(sensorFiles[i].modified).toLocaleString();
          pairs.push({
            timestamp,
            maxFile: sensorFiles[i].name,
            minFile: sensorFiles[i + 1].name
          });
        }
      }
      
      setFileHistory(pairs.slice(0, 5));
      
      // Fetch per-file stats for recent files to build historical trend
      const recentFiles = sensorFiles.slice(0, 6); // up to 6 recent files
      const statsPromises = recentFiles.map(f =>
        fetch(`${API_BASE_URL}/api/file-stats?filename=${encodeURIComponent(f.name)}`).then(r => r.ok ? r.json() : null).catch(() => null)
      );

      const statsResults = await Promise.all(statsPromises);
      const filtered = statsResults.filter(r => r && r.status === 'success');
      // Map to an ordered array oldest->newest
      const ordered = filtered.reverse();
      setHistoricalStats(ordered);
    } catch (err) {
      console.error('Error fetching file history:', err);
    }
  };

  const fetchEvents = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/events`);
      if (!response.ok) throw new Error('Failed to fetch events');

      const result = await response.json();
      setEvents(Array.isArray(result.events) ? result.events : []);
    } catch (err) {
      console.error('Error fetching events:', err);
    }
  };

  // Effects (unchanged)
  useEffect(() => {
    fetchSensorData(mode);
  }, [mode]);

  useEffect(() => {
    fetchFileHistory(selectedSensor);
  }, [selectedSensor]);

  useEffect(() => {
    fetchEvents();
  }, []);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchSensorData(mode);
      }, 2 * 60 * 60 * 1000); // Refresh every 2 hours
      return () => clearInterval(interval);
    }
  }, [autoRefresh, mode]);

  // Event handlers
  const handleModeChange = (e) => {
    setMode(e.target.value);
  };

  const handleSensorChange = (e) => {
    setSelectedSensor(e.target.value);
  };

  const handleParamChange = (e) => {
    setSelectedParam(e.target.value);
  };

  const handleTimeSeriesSensorChange = (newSensor) => {
    setTimeSeriesSensor(newSensor);
  };

  const openModal = (title, content) => {
    setModalTitle(title);
    setModalContent(content);
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setModalContent(null);
  };

  const currentSensorData = sensorData[selectedSensor] || {};

  // ============================================================
  // RENDER - Professional Industrial Dashboard Layout
  // ============================================================
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* HEADER SECTION - Professional Title Bar */}
      <header className="bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 border-b-2 border-cyan-600 shadow-2xl sticky top-0 z-40">
        <div className="max-w-full mx-auto px-4 py-6">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            {/* Left: Title and Subtitle */}
            <div className="flex-1">
              <h1 className="text-3xl md:text-4xl font-black text-white tracking-tight drop-shadow-lg">
                ⚡ Predictive Maintenance Dashboard
              </h1>
              <p className="text-cyan-300 text-sm md:text-base mt-1 font-medium drop-shadow">
                Real-time industrial sensor monitoring and FFT analysis platform
              </p>
            </div>

            {/* Right: Last Updated and Refresh */}
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider">Last Updated</p>
                <p className="text-emerald-400 text-lg font-bold font-mono">{lastUpdate || '—'}</p>
              </div>
              <button
                onClick={() => fetchSensorData(mode)}
                className="h-12 px-5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-semibold rounded-lg transition duration-200 flex items-center gap-2 shadow-lg hover:shadow-xl transform hover:scale-105"
              >
                <span>🔄</span>
                <span className="hidden sm:inline">Refresh</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* CONTROLS SECTION - Global Settings */}
      <div className="bg-gradient-to-r from-slate-800 via-slate-700 to-slate-800 border-b-2 border-cyan-500 px-4 py-4 shadow-lg">
        <div className="max-w-full mx-auto">
          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
            {/* View Mode Selector */}
            <div className="sm:w-40">
              <label className="block text-slate-200 text-xs font-bold uppercase tracking-wider mb-1">🎛️ Mode</label>
              <select
                value={mode}
                onChange={handleModeChange}
                className="w-full h-10 bg-gradient-to-r from-slate-600 to-slate-700 text-white text-sm border-2 border-slate-500 rounded-lg px-3 py-1 font-medium shadow-md hover:border-cyan-400 hover:shadow-lg focus:border-cyan-400 focus:ring-2 focus:ring-cyan-300/50 focus:outline-none transition duration-200 cursor-pointer"
              >
                {MODES.map(m => (
                  <option key={m.value} value={m.value} className="bg-slate-700 text-white">
                    {m.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Auto-Refresh Toggle */}
            <div className="flex flex-wrap items-center gap-2 pt-2 sm:pt-0 sm:ml-auto relative">
              <div className="relative">
                <button
                  type="button"
                  onClick={openEventModal}
                  className="h-10 px-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white text-sm font-medium rounded-lg transition duration-200 shadow-md hover:shadow-lg flex items-center gap-2"
                >
                  📅 Event
                  <span className="text-xs">+</span>
                </button>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-12 h-6 bg-gradient-to-r from-slate-400 to-slate-600 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-cyan-400 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-gradient-to-r peer-checked:from-cyan-500 peer-checked:to-blue-600 shadow-md"></div>
                <span className="ml-3 text-slate-200 font-medium text-xs">Auto-refresh (2h)</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* ERROR DISPLAY */}
      {error && (
        <div className="mx-4 mt-6 bg-gradient-to-r from-red-900 to-red-800 border-l-4 border-red-500 text-red-100 p-5 rounded-lg shadow-lg max-w-full mx-auto backdrop-blur-sm">
          <p className="font-bold flex items-center gap-3 text-lg">
            <span>🚨</span> <span>Error:</span> {error}
          </p>
        </div>
      )}

      {/* LOADING STATE */}
      {loading && Object.keys(sensorData).length === 0 && (
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-16 w-16 border-4 border-cyan-400 border-t-blue-600 mb-6"></div>
            <p className="text-cyan-300 text-lg font-semibold drop-shadow">Loading sensor data...</p>
            <p className="text-slate-400 text-sm mt-2">Fetching real-time monitoring information</p>
          </div>
        </div>
      )}

      {/* MAIN DASHBOARD GRID - 30/70 Layout */}
      {!loading && Object.keys(sensorData).length > 0 && (
        <main className="max-w-full mx-auto px-4 py-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 auto-rows-min">
            {/* ================================================
                LEFT SIDEBAR (30% width) - Sensor Controls & Data
                ================================================ */}
            <div className="lg:col-span-1 space-y-6">
              {/* SENSOR SELECTION CARD */}
              <div className="bg-white rounded-xl shadow-lg overflow-hidden border-l-4 border-blue-600 hover:shadow-xl transition duration-200">
                <div className="bg-gradient-to-r from-blue-600 via-blue-500 to-cyan-500 px-6 py-4 border-b-2 border-blue-400">
                  <h2 className="text-lg font-bold text-white">🔌 Sensor Selection</h2>
                  <p className="text-xs text-blue-100 mt-1">Choose sensor for detailed analysis</p>
                </div>
                <div className="p-5">
                  <select
                    value={selectedSensor}
                    onChange={handleSensorChange}
                    className="w-40 h-10 bg-gradient-to-r from-gray-50 to-blue-50 text-gray-900 text-sm border-2 border-blue-300 rounded-lg px-3 py-2 font-medium shadow-sm hover:border-blue-500 hover:shadow-md focus:border-blue-600 focus:ring-2 focus:ring-blue-200 focus:outline-none transition duration-200 cursor-pointer"
                  >
                    {SENSORS.map(sensor => (
                      <option key={sensor} value={sensor} className="text-gray-900">
                        {sensor.charAt(0).toUpperCase() + sensor.slice(1)} Sensor
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* FILE HISTORY CARD */}
              <FileHistoryTable files={fileHistory} sensor={selectedSensor} />

              {/* EVENT HISTORY CARD */}
              <EventHistoryTable events={events} onRefresh={fetchEvents} />

              {/* STATISTICS TABLE CARD */}
              <div className="">
                <EnhancedStatisticsTable
                  sensorData={sensorData}
                  selectedSensor={selectedSensor}
                  mode={mode}
                />
              </div>

              {/* Fullscreen modal */}
              <FullscreenModal open={modalOpen} onClose={closeModal} title={modalTitle}>
                {modalContent}
              </FullscreenModal>
            </div>

            {/* ================================================
                RIGHT CONTENT AREA (70% width) - Charts & Analysis
                ================================================ */}
            <div className="lg:col-span-2 space-y-6">
              {/* TIME SERIES CHART CARD */}
              <div className="bg-white rounded-xl shadow-lg overflow-hidden border-l-4 border-blue-600 hover:shadow-xl transition duration-200 min-h-[380px]">
                <div onDoubleClick={() => openModal(`Time Series - ${timeSeriesSensor}`, (
                  <div style={{ height: '80vh' }}>
                    <TimeSeriesChart
                      sensor={timeSeriesSensor}
                      sensorData={sensorData[timeSeriesSensor] || {}}
                      onSensorChange={handleTimeSeriesSensorChange}
                    />
                  </div>
                ))}>
                  <TimeSeriesChart 
                    sensor={timeSeriesSensor} 
                    sensorData={sensorData[timeSeriesSensor] || {}}
                    onSensorChange={handleTimeSeriesSensorChange}
                  />
                </div>
              </div>

              {/* STATISTICAL TREND ANALYSIS CARD */}
              <div className="bg-white rounded-xl shadow-md overflow-hidden min-h-[380px]">
                {/* Parameter Selector Header */}
                <div className="bg-gradient-to-r from-emerald-600 via-emerald-500 to-teal-500 px-8 py-5 border-b-2 border-emerald-400">
                  <h2 className="text-lg font-bold text-white mb-3">📊 Statistical Trend Analysis</h2>
                  <div className="w-52">
                    <label className="block text-xs font-semibold text-emerald-100 mb-2">Parameter:</label>
                    <select
                      value={selectedParam}
                      onChange={handleParamChange}
                      className="w-40 h-10 bg-gradient-to-r from-gray-50 to-blue-50 text-gray-900 text-sm border-2 border-blue-300 rounded-lg px-3 py-2 font-medium shadow-sm hover:border-blue-500 hover:shadow-md focus:border-blue-600 focus:ring-2 focus:ring-blue-200 focus:outline-none transition duration-200 cursor-pointer"
                    >
                      {STAT_PARAMETERS.map(param => (
                        <option key={param.key} value={param.key} className="text-gray-900">
                          {param.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Chart Container */}
                <div className="p-6">
                  <div onDoubleClick={() => openModal(`Statistical Trend - ${selectedParam}`, (
                    <div style={{ height: '80vh' }}>
                      <StatisticalAnalysisChart
                        sensor={timeSeriesSensor}
                        sensorData={sensorData[timeSeriesSensor] || {}}
                        selectedParam={selectedParam}
                        historicalStats={historicalStats}
                      />
                    </div>
                  ))} className="relative min-h-[320px]">
                    <StatisticalAnalysisChart
                      sensor={timeSeriesSensor}
                      sensorData={sensorData[timeSeriesSensor] || {}}
                      selectedParam={selectedParam}
                      historicalStats={historicalStats}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      )}

      <EventModal
        open={eventModalOpen}
        onClose={closeEventModal}
        eventName={eventName}
        customEventName={customEventName}
        eventTime={eventTime}
        eventDescription={eventDescription}
        submitting={eventSubmitting}
        onEventNameChange={setEventName}
        onCustomEventNameChange={setCustomEventName}
        onEventTimeChange={setEventTime}
        onEventDescriptionChange={setEventDescription}
        onSubmit={handleCreateEvent}
      />
    </div>
  );
}

export default App;
