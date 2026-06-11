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

// Determine API base URL - always use Render for backend, frontend runs locally
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
 * - PHASE 3: Can display fault current data when monitoring
 */
function TimeSeriesChart({ sensor, sensorData, onSensorChange, faultCurrentData = null, activeFault = null }) {
  // Check if we're in fault monitoring mode
  const isFaultMode = faultCurrentData && activeFault;

  // Plot raw sensor values against time
  const rawValues = isFaultMode 
    ? (faultCurrentData?.values || []) 
    : (sensorData?.raw_values || []);
  const rawTimestamps = isFaultMode 
    ? (faultCurrentData?.timestamps || []) 
    : (sensorData?.raw_timestamps || []);

  if ((!isFaultMode && (!sensorData || rawValues.length === 0)) || (isFaultMode && rawValues.length === 0)) {
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

  const currentSensor = isFaultMode ? (faultCurrentData?.sensor_type || 'acceleration') : sensor;
  const chartData = {
    labels,
    datasets: [
      {
        label: isFaultMode 
          ? `${currentSensor.charAt(0).toUpperCase() + currentSensor.slice(1)} - ${activeFault}` 
          : `${sensor.charAt(0).toUpperCase() + sensor.slice(1)} Sensor Readings`,
        data: rawValues,
        borderColor: isFaultMode ? '#ef4444' : '#06b6d4',
        backgroundColor: isFaultMode ? 'rgba(239, 68, 68, 0.08)' : 'rgba(6, 182, 212, 0.08)',
        fill: true,
        tension: 0.3,
        pointRadius: 1,
        pointBackgroundColor: isFaultMode ? '#ef4444' : '#06b6d4',
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
          label: (item) => `${currentSensor}: ${item.formattedValue}`
        }
      }
    },
    scales: {
      y: {
        title: { display: true, text: `${currentSensor} Value`, font: { size: 12, weight: '600', color: '#374151' } },
        grid: { color: 'rgba(0,0,0,0.08)', drawBorder: false },
        ticks: { font: { size: 11, color: '#6b7280' } }
      },
      x: {
        title: { display: true, text: 'Time (ms)', font: { size: 12, weight: '600', color: '#374151' } },
        grid: { display: false, drawBorder: false },
        ticks: { font: { size: 11, color: '#6b7280' }, maxRotation: 0, minRotation: 0, autoSkip: true, maxTicksLimit: 8 }
      }
    }
  };

  return (
    <div className={`${isFaultMode ? 'bg-gradient-to-br from-red-50 to-pink-50 border-l-4 border-red-500' : 'bg-white'} rounded-xl shadow-md p-6 flex flex-col h-full cursor-pointer transition duration-300`} onDoubleClick={() => { /* placeholder for parent handler */ }}>
      {/* Card Header */}
      <div className={`mb-6 pb-4 border-b-2 ${isFaultMode ? 'border-red-200' : 'border-blue-200'}`}>
        <h2 className={`text-xl font-bold ${isFaultMode ? 'text-red-900' : 'text-gray-900'} mb-4 flex items-center gap-2`}>
          {isFaultMode ? '🎯' : '📈'} Time Series Analysis
          {isFaultMode && <span className="text-sm ml-2 px-2 py-1 bg-red-200 text-red-800 rounded-full">Live Fault</span>}
        </h2>
        
        {/* Parameter Selector Dropdown */}
        {!isFaultMode && (
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
        )}
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
 * - PHASE 3: Can display fault trend data when monitoring
 */
function StatisticalAnalysisChart({ sensor, sensorData, selectedParam, historicalStats = [], faultTrendData = null, activeFault = null }) {
  // Check if we're in fault monitoring mode
  const isFaultMode = faultTrendData && activeFault && faultTrendData.intervals && faultTrendData.intervals.length > 0;

  if (isFaultMode) {
    // FAULT MODE: Display fault progression data
    const intervals = faultTrendData.intervals;
    
    // Map intervals to chart data based on selected metric
    let datasetLabel = 'Fault Progression - Acceleration RMS';
    let datasetValues = [];
    let borderColor = '#ef4444';
    let backgroundColor = 'rgba(239, 68, 68, 0.08)';
    let pointColor = '#ef4444';

    // Use different metrics based on selection
    if (selectedParam === 'mean' || selectedParam === 'kurtosis') {
      datasetLabel = `Fault Progression - Accel ${selectedParam.toUpperCase()}`;
      datasetValues = intervals.map(i => 
        selectedParam === 'kurtosis' ? i.accel_kurtosis : (i.accel_std_dev || 0)
      );
    } else if (selectedParam === 'range' || selectedParam === 'std_dev') {
      datasetLabel = `Fault Progression - ${selectedParam === 'range' ? 'Range' : 'Std Dev'}`;
      datasetValues = intervals.map(i => i.accel_std_dev || 0);
    } else {
      // Default to RMS for other parameters
      datasetValues = intervals.map(i => i.accel_rms || 0);
    }

    const labels = intervals.map(i => `Int ${i.interval}`);

    const chartData = {
      labels,
      datasets: [
        {
          label: datasetLabel,
          data: datasetValues,
          borderColor,
          backgroundColor,
          fill: true,
          tension: 0.3,
          pointRadius: 6,
          pointBackgroundColor: pointColor,
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          borderWidth: 2.5
        }
      ]
    };

    const options = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { 
          display: true, 
          position: 'top', 
          labels: { padding: 16, font: { size: 12, weight: '600' } } 
        }
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

    return (
      <div className="bg-gradient-to-br from-red-50 to-pink-50 rounded-xl shadow-lg overflow-hidden border-l-4 border-red-500 p-6 flex flex-col h-full hover:shadow-xl transition duration-200">
        <div className="mb-6 pb-4 border-b-2 border-red-200">
          <h2 className="text-xl font-bold text-red-900 mb-3 flex items-center gap-2">
            🎯 Fault Event Trend Analysis
            <span className="text-sm ml-2 px-2 py-1 bg-red-200 text-red-800 rounded-full">Live</span>
          </h2>
          <p className="text-sm text-red-700 font-medium">Fault: <span className="text-red-900 font-semibold">{activeFault}</span> | Intervals: <span className="text-red-900 font-semibold">{intervals.length}</span></p>
        </div>
        <div className="relative flex-1 min-h-[380px]">
          <Line data={chartData} options={options} />
        </div>
      </div>
    );
  } else {
    // ORIGINAL MODE: Display historical statistics
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
            <label className="mb-2 block text-sm font-medium text-slate-700">Fault Type</label>
            <select
              value={eventName}
              onChange={(e) => onEventNameChange(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2 text-slate-900 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-200"
            >
              <option value="">-- Select fault type --</option>
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
                placeholder="Enter custom fault name..."
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
              placeholder="Enter additional details about the fault event..."
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
 * Displays database statistics in a beautiful table format
 * - All parameters fetched from PostgreSQL database
 * - Professional table design with organized sections
 * - Proper data alignment and formatting
 */
function EnhancedStatisticsTable({ dbStats, selectedSensor, mode }) {
  const sensorStats = dbStats[selectedSensor];

  if (!sensorStats) {
    return (
      <div className="bg-white rounded-xl shadow-lg overflow-hidden border-l-4 border-emerald-600">
        <div className="bg-gradient-to-r from-emerald-600 via-emerald-500 to-teal-500 px-6 py-4 border-b-2 border-emerald-400">
          <h3 className="text-lg font-bold text-white flex items-center gap-2">📊 Database Statistics</h3>
        </div>
        <div className="p-8 text-center text-gray-400">No data available for {selectedSensor}</div>
      </div>
    );
  }

  const formatValue = (value) => {
    return value !== undefined && value !== null 
      ? (typeof value === 'number' ? value.toFixed(4) : value)
      : '—';
  };

  const statisticRows = [
    { label: 'Mean', key: 'mean', icon: '📈' },
    { label: 'Maximum', key: 'max', icon: '⬆️' },
    { label: 'Minimum', key: 'min', icon: '⬇️' },
    { label: 'Std Deviation', key: 'std_dev', icon: '📊' },
    { label: 'Skewness', key: 'skewness', icon: '🔄' },
    { label: 'Kurtosis', key: 'kurtosis', icon: '📐' },
  ];

  const frequencyRows = [
    { label: 'Frequency 1', key: 'frequency1', icon: '🔊' },
    { label: 'Frequency 2', key: 'frequency2', icon: '🔊' },
    { label: 'Frequency 3', key: 'frequency3', icon: '🔊' },
    { label: 'Frequency 4', key: 'frequency4', icon: '🔊' },
    { label: 'Frequency 5', key: 'frequency5', icon: '🔊' },
  ];

  const amplitudeRows = [
    { label: 'Amplitude 1', key: 'amplitude1', icon: '📡' },
    { label: 'Amplitude 2', key: 'amplitude2', icon: '📡' },
    { label: 'Amplitude 3', key: 'amplitude3', icon: '📡' },
    { label: 'Amplitude 4', key: 'amplitude4', icon: '📡' },
    { label: 'Amplitude 5', key: 'amplitude5', icon: '📡' },
  ];

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden border-l-4 border-emerald-600">
      {/* HEADER */}
      <div className="bg-gradient-to-r from-emerald-600 via-emerald-500 to-teal-500 px-6 py-5 border-b-2 border-emerald-400">
        <h3 className="text-lg font-bold text-white flex items-center gap-2">📊 Database Statistics</h3>
        <p className="text-xs text-emerald-100 mt-2">Sensor: <span className="font-semibold uppercase">{selectedSensor}</span></p>
      </div>

      {/* TABLE CONTENT */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          {/* CORE STATISTICS SECTION */}
          <thead>
            <tr className="bg-emerald-50 border-b-2 border-emerald-300">
              <th colSpan="2" className="px-5 py-3 text-left font-bold text-emerald-900 text-base">📈 Core Statistics</th>
            </tr>
          </thead>
          <tbody>
            {statisticRows.map((row, idx) => (
              <tr key={row.key} className={idx % 2 === 0 ? 'bg-white hover:bg-emerald-50' : 'bg-gray-50 hover:bg-emerald-50'}>
                <td className="px-5 py-3 font-semibold text-gray-800 flex items-center gap-2 border-b border-gray-200">
                  <span className="text-lg">{row.icon}</span>
                  {row.label}
                </td>
                <td className="px-5 py-3 text-right font-bold text-gray-900 tabular-nums border-b border-gray-200">{formatValue(sensorStats[row.key])}</td>
              </tr>
            ))}
          </tbody>

          {/* FREQUENCY COMPONENTS SECTION */}
          <thead>
            <tr className="bg-yellow-50 border-b-2 border-yellow-300">
              <th colSpan="2" className="px-5 py-3 text-left font-bold text-yellow-900 text-base">🔊 Frequency Components (Hz)</th>
            </tr>
          </thead>
          <tbody>
            {frequencyRows.map((row, idx) => (
              <tr key={row.key} className={idx % 2 === 0 ? 'bg-white hover:bg-yellow-50' : 'bg-gray-50 hover:bg-yellow-50'}>
                <td className="px-5 py-3 font-semibold text-gray-800 flex items-center gap-2 border-b border-gray-200">
                  <span className="text-lg">{row.icon}</span>
                  {row.label}
                </td>
                <td className="px-5 py-3 text-right font-bold text-gray-900 tabular-nums border-b border-gray-200">{formatValue(sensorStats[row.key])}</td>
              </tr>
            ))}
          </tbody>

          {/* AMPLITUDE COMPONENTS SECTION */}
          <thead>
            <tr className="bg-blue-50 border-b-2 border-blue-300">
              <th colSpan="2" className="px-5 py-3 text-left font-bold text-blue-900 text-base">📡 Amplitude Components</th>
            </tr>
          </thead>
          <tbody>
            {amplitudeRows.map((row, idx) => (
              <tr key={row.key} className={idx % 2 === 0 ? 'bg-white hover:bg-blue-50' : 'bg-gray-50 hover:bg-blue-50'}>
                <td className="px-5 py-3 font-semibold text-gray-800 flex items-center gap-2 border-b border-gray-200">
                  <span className="text-lg">{row.icon}</span>
                  {row.label}
                </td>
                <td className="px-5 py-3 text-right font-bold text-gray-900 tabular-nums border-b border-gray-200">{formatValue(sensorStats[row.key])}</td>
              </tr>
            ))}
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
  const [dbStats, setDbStats] = useState({});  // New: Database statistics
  const [recentFiles, setRecentFiles] = useState([]);  // New: Recent CSV files from database query
  const [lastDataTimestamp, setLastDataTimestamp] = useState(null);
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
  
  // Phase 2: Fault Event Monitoring
  const [activeFault, setActiveFault] = useState(null);
  const [faultTrendData, setFaultTrendData] = useState(null);
  const [faultCurrentData, setFaultCurrentData] = useState(null);
  const [eventMonitoringActive, setEventMonitoringActive] = useState(false);
  const [eventFailureDetected, setEventFailureDetected] = useState(false);
  const [eventIntervalCount, setEventIntervalCount] = useState(0);
  const [faultStatusMessage, setFaultStatusMessage] = useState('');


  
  // Countdown timer for next data point (30-second intervals)
  const [countdownSeconds, setCountdownSeconds] = useState(0);
  const [failureInfoDisplay, setFailureInfoDisplay] = useState(null);

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

    if (!faultType) {
      alert('Please select a fault type');
      return;
    }

    setEventSubmitting(true);

    try {
      // Call the new event creation from history endpoint
      const response = await fetch(`${API_BASE_URL}/api/create-event-from-history`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          fault_name: faultType
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to create event from historical data');
      }

      // Format deviation points and intervals for display
      const deviationInfo = data.deviation_points 
        ? Object.entries(data.deviation_points).map(([sensor, idx]) => `${sensor}: ${idx}`).join(', ')
        : 'N/A';
      
      const intervalsInfo = data.intervals_extracted
        ? Object.entries(data.intervals_extracted).map(([sensor, count]) => `${sensor}: ${count}`).join(', ')
        : 'N/A';

      // Build success message with database info
      let successMsg = `✓ Event "${faultType}" created successfully!\n\n`;
      successMsg += `📊 Data Analysis:\n`;
      successMsg += `  Deviation at: ${deviationInfo}\n`;
      successMsg += `  Intervals extracted: ${intervalsInfo}\n`;
      
      if (data.fault_id !== null && data.rows_inserted) {
        successMsg += `\n💾 Database:\n`;
        successMsg += `  Fault ID: ${data.fault_id}\n`;
        successMsg += `  Rows inserted: ${data.rows_inserted}\n`;
        successMsg += `  Table: ${data.database_table || 'N/A'}`;
      }
      
      alert(successMsg);
      
      // Refresh events to show the new extraction
      await fetchEvents();
      closeEventModal();
    } catch (error) {
      console.error('Error creating event from history:', error);
      alert(`Error: ${error.message}`);
    } finally {
      setEventSubmitting(false);
    }
  };

  // Download CSV files generated from event creation

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

  // NEW: Fetch database statistics and recent files
  const fetchDatabaseStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/combined-dashboard-data`);
      if (!response.ok) throw new Error('Failed to fetch database stats');
      
      const result = await response.json();
      if (result.success) {
        setDbStats(result.database_stats || {});
        setRecentFiles(result.recent_files || []);
        console.log('✓ Database stats fetched:', result.database_stats);
      }
    } catch (err) {
      console.warn('Could not fetch database stats:', err);
    }
  };

  const fetchFileHistory = async (sensor) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/historical-stats?sensor=${encodeURIComponent(sensor)}&limit=25`);
      if (!response.ok) throw new Error('Failed to fetch historical stats');
      
      const result = await response.json();
      if (result.status === 'success' && Array.isArray(result.data)) {
        const statsData = result.data;
        // setHistoricalStats expects oldest -> newest
        setHistoricalStats(statsData);
        
        // Generate virtual file history pairs (newest -> oldest) for the sidebar table
        const recentStats = [...statsData].reverse().slice(0, 5);
        const virtualHistory = recentStats.map(item => {
          const formattedDate = item.file_timestamp ? new Date(item.file_timestamp).toLocaleString() : '—';
          return {
            timestamp: formattedDate,
            maxFile: `max_${sensor}.csv`,
            minFile: `min_${sensor}.csv`
          };
        });
        setFileHistory(virtualHistory);
      }
    } catch (err) {
      console.error('Error fetching file history from database:', err);
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

  // NEW: Fetch database statistics on mount
  useEffect(() => {
    fetchDatabaseStats();
    // Refresh database stats every 2 hours (same as sensor data)
    const interval = setInterval(fetchDatabaseStats, 2 * 60 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchSensorData(mode);
      }, 2 * 60 * 60 * 1000); // Refresh every 2 hours
      return () => clearInterval(interval);
    }
  }, [autoRefresh, mode]);

  // Real-time Auto-refresh: Poll server for latest data arrival timestamp
  useEffect(() => {
    const checkLatestDataTimestamp = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/latest-data-timestamp`);
        if (response.ok) {
          const result = await response.json();
          if (result.status === 'success' && result.timestamp) {
            // Update on first load or if a newer timestamp is detected
            setLastDataTimestamp(prev => {
              if (prev !== null && prev !== result.timestamp) {
                console.log(`🔄 New sensor data detected! Previous: ${prev}, New: ${result.timestamp}. Triggering refresh...`);
                // Trigger refresh across the entire dashboard
                fetchSensorData(mode);
                fetchDatabaseStats();
                fetchFileHistory(selectedSensor);
                fetchEvents();
              }
              return result.timestamp;
            });
          }
        }
      } catch (err) {
        console.warn('Could not query latest data timestamp:', err);
      }
    };

    // Run initial check immediately
    checkLatestDataTimestamp();

    // Poll every 5 seconds
    const interval = setInterval(checkLatestDataTimestamp, 5000);
    return () => clearInterval(interval);
  }, [mode, selectedSensor]);

  // ======================== PHASE 2: FAULT EVENT MONITORING ========================
  // Poll fault state every 30 seconds when activeFault is selected
  useEffect(() => {
    if (!activeFault) {
      setEventMonitoringActive(false);
      return;
    }

    setEventMonitoringActive(true);
    setEventFailureDetected(false);
    setFaultStatusMessage(`Starting monitoring for ${activeFault}...`);
    setCountdownSeconds(0);
    setFailureInfoDisplay(null);

    let hasFailureOccurred = false;  // Track failure locally to avoid effect re-runs
    let pollInterval = null;

    const pollFaultData = async () => {
      try {
        // Fetch state and trend data in parallel
        const [stateRes, trendRes, currentRes] = await Promise.all([
          fetch(`${API_BASE_URL}/api/fault-state/${activeFault}`),
          fetch(`${API_BASE_URL}/api/fault-trend/${activeFault}`),
          fetch(`${API_BASE_URL}/api/fault-current/${activeFault}?sensor=acceleration`)
        ]);

        if (stateRes.ok) {
          const state = await stateRes.json();
          setEventIntervalCount(state.interval_count || 0);
          
          // Display failure info when failure detected
          if (state.system_failure_state && state.failure_interval && !hasFailureOccurred) {
            hasFailureOccurred = true;
            setFailureInfoDisplay({
              interval: state.failure_interval,
              message: `🔥 FAILURE DETECTED at interval ${state.failure_interval}`
            });
            setEventFailureDetected(true);
            // Stop polling after failure is detected
            if (pollInterval) {
              clearInterval(pollInterval);
              setEventMonitoringActive(false);
            }
          }
          
          setFaultStatusMessage(
            state.system_failure_state 
              ? `🔥 FAILURE at interval ${state.failure_interval}` 
              : `📊 Interval ${state.interval_count} | ⏱️ Next in ${countdownSeconds}s`
          );
        }

        if (trendRes.ok) {
          const trend = await trendRes.json();
          setFaultTrendData(trend);
        }

        if (currentRes.ok) {
          const current = await currentRes.json();
          setFaultCurrentData(current);
        }
        
        // Reset countdown after successful poll (10 seconds until next)
        setCountdownSeconds(10);
      } catch (error) {
        console.error('Polling error:', error);
        setFaultStatusMessage('Polling stopped: Connection error');
      }
    };

    // Poll immediately, then every 10 seconds
    pollFaultData();
    pollInterval = setInterval(pollFaultData, 10000);

    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [activeFault]);

  // Countdown timer for next data point (decrements every second)
  useEffect(() => {
    if (!activeFault) {
      return;
    }

    const countdownInterval = setInterval(() => {
      setCountdownSeconds(prev => {
        if (prev <= 1) {
          return 10; // Reset when reaches 0
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(countdownInterval);
  }, [activeFault]);

  // ======================== EVENT HANDLERS ========================

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

  const handleFaultSelect = (faultName) => {
    if (activeFault === faultName) {
      setActiveFault(null);
      setEventMonitoringActive(false);
    } else {
      setActiveFault(faultName);
      setEventFailureDetected(false);
      setEventIntervalCount(0);
      setFaultTrendData(null);
      setFaultCurrentData(null);
    }
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
        <main className="max-w-full mx-auto px-4 py-6 pb-0">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
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

              {/* STATISTICS TABLE - Displays Database Statistics */}
              <EnhancedStatisticsTable
                dbStats={dbStats}
                selectedSensor={selectedSensor}
                mode={mode}
              />

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
                      sensorData={sensorData[timeSeriesSensor]?.[mode] || {}}
                      onSensorChange={handleTimeSeriesSensorChange}
                      faultCurrentData={faultCurrentData}
                      activeFault={activeFault}
                    />
                  </div>
                ))}>
                  <TimeSeriesChart 
                    sensor={timeSeriesSensor} 
                    sensorData={sensorData[timeSeriesSensor]?.[mode] || {}}
                    onSensorChange={handleTimeSeriesSensorChange}
                    faultCurrentData={faultCurrentData}
                    activeFault={activeFault}
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
                        sensorData={sensorData[timeSeriesSensor]?.[mode] || {}}
                        selectedParam={selectedParam}
                        historicalStats={historicalStats}
                        faultTrendData={faultTrendData}
                        activeFault={activeFault}
                      />
                    </div>
                  ))} className="relative min-h-[320px]">
                    <StatisticalAnalysisChart
                      sensor={timeSeriesSensor}
                      sensorData={sensorData[timeSeriesSensor]?.[mode] || {}}
                      selectedParam={selectedParam}
                      historicalStats={historicalStats}
                      faultTrendData={faultTrendData}
                      activeFault={activeFault}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      )}

      {/* PAGE FOOTER - Spans Full Width */}
      <footer className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border-t-2 border-cyan-600 mt-8 shadow-2xl">
        <div className="max-w-full mx-auto px-4 py-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {/* Column 1: System Info */}
            <div>
              <h4 className="text-white font-bold text-lg mb-3 flex items-center gap-2">⚡ System</h4>
              <div className="space-y-2 text-sm text-slate-300">
                <p><span className="font-semibold">Status:</span> <span className="text-emerald-400">🟢 Active</span></p>
                <p><span className="font-semibold">Sensors:</span> 3 (Acceleration, Current, Audio)</p>
                <p><span className="font-semibold">Database:</span> PostgreSQL Neon</p>
              </div>
            </div>

            {/* Column 2: Data Source */}
            <div>
              <h4 className="text-white font-bold text-lg mb-3 flex items-center gap-2">🗄️ Data</h4>
              <div className="space-y-2 text-sm text-slate-300">
                <p><span className="font-semibold">Source:</span> PostgreSQL Database</p>
                <p><span className="font-semibold">Sample Rate:</span> 1400 Hz (2-sec windows)</p>
                <p><span className="font-semibold">Update:</span> Real-time</p>
              </div>
            </div>

            {/* Column 3: Features */}
            <div>
              <h4 className="text-white font-bold text-lg mb-3 flex items-center gap-2">✨ Features</h4>
              <div className="space-y-2 text-sm text-slate-300">
                <p>📊 Statistical Analysis</p>
                <p>📈 Time Series Visualization</p>
                <p>🎯 FFT Frequency Analysis</p>
                <p>📅 Event Creation & Tracking</p>
              </div>
            </div>

            {/* Column 4: Contact */}
            <div>
              <h4 className="text-white font-bold text-lg mb-3 flex items-center gap-2">📞 Platform</h4>
              <div className="space-y-2 text-sm text-slate-300">
                <p><span className="font-semibold">Version:</span> 3.0 (Phase 3)</p>
                <p><span className="font-semibold">Framework:</span> React + Flask</p>
                <p><span className="font-semibold">Deployment:</span> Render + Neon</p>
              </div>
            </div>
          </div>

          {/* Bottom Section */}
          <div className="border-t border-slate-700 mt-8 pt-6 flex flex-col sm:flex-row justify-between items-center gap-4 text-xs text-slate-400">
            <p>© 2026 Predictive Maintenance Dashboard • All Rights Reserved</p>
            <div className="flex items-center gap-4">
              <a href="#" className="hover:text-cyan-400 transition">Privacy Policy</a>
              <span>•</span>
              <a href="#" className="hover:text-cyan-400 transition">Terms of Service</a>
              <span>•</span>
              <a href="#" className="hover:text-cyan-400 transition">Documentation</a>
            </div>
          </div>
        </div>
      </footer>

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
