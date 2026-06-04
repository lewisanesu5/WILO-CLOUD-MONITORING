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

// ============================================================
// REUSABLE COMPONENTS - Enhanced with Professional Styling
// ============================================================

/**
 * TimeSeriesChart Component
 * Displays min/mean/max sensor data with parameter selector
 * - Maintains original chart logic and data processing
 * - Enhanced UI with professional card styling
 */
function TimeSeriesChart({ sensor, sensorData, onSensorChange }) {
  // Prefer plotting raw values (timestamps + values) when available
  const hasRaw = sensorData && Array.isArray(sensorData.raw_values) && sensorData.raw_values.length > 0;

  if (!sensorData || (!hasRaw && !sensorData.stats)) {
    return (
      <div className="bg-white rounded-xl shadow-md p-8 h-full flex items-center justify-center">
        <p className="text-gray-400 text-center">No data available</p>
      </div>
    );
  }

  let chartData;
  if (hasRaw) {
    const timestamps = sensorData.raw_timestamps || [];
    const values = sensorData.raw_values || [];
    // Normalize timestamps to seconds from start (0 - 2s)
    const start = timestamps.length ? timestamps[0] : 0;
    const labels = timestamps.map(t => ((t - start) / 1000).toFixed(3));

    chartData = {
      labels,
      datasets: [
        {
          label: `${sensor} - Raw (0-2s)`,
          data: values,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.06)',
          fill: true,
          tension: 0.2,
          pointRadius: 0,
          borderWidth: 2
        }
      ]
    };
  } else {
    const data = sensorData.stats;
    chartData = {
      labels: ['Min', 'Mean', 'Max'],
      datasets: [
        {
          label: `${sensor} - Time Series`,
          data: [data.min || 0, data.mean || 0, data.max || 0],
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          fill: true,
          tension: 0.4,
          pointRadius: 5,
          pointBackgroundColor: '#3b82f6',
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointHoverRadius: 7
        }
      ]
    };
  }

  const options = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: { display: true, position: 'top', labels: { padding: 16, font: { size: 12, weight: '600' } } }
    },
    scales: {
      y: {
        title: { display: true, text: 'Value', font: { size: 12, weight: '600' } },
        grid: { color: 'rgba(0,0,0,0.05)' }
      },
      x: {
        title: { display: true, text: hasRaw ? 'Seconds (s)' : 'Category', font: { size: 12, weight: '600' } },
        grid: { display: false }
      }
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-8 flex flex-col h-full">
      {/* Card Header */}
      <div className="mb-6 pb-4 border-b-2 border-gray-100">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Time Series Analysis</h2>
        
        {/* Parameter Selector Dropdown */}
        <div className="w-full">
          <label className="block text-sm font-semibold text-gray-700 mb-2">Select Parameter:</label>
          <select
            value={sensor}
            onChange={(e) => onSensorChange(e.target.value)}
            className="w-full h-12 bg-gray-50 text-gray-900 border-2 border-gray-300 rounded-lg px-4 py-3 font-medium hover:border-blue-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 focus:outline-none transition duration-200 cursor-pointer appearance-none bg-no-repeat bg-right-4 pr-10"
            style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%236B7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E")`,
            }}
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
      <div style={{ height: '320px', flex: 1 }} className="relative">
        <Line data={chartData} options={options} />
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
function StatisticalAnalysisChart({ sensor, sensorData, selectedParam }) {
  if (!sensorData || !sensorData.stats) {
    return (
      <div className="bg-white rounded-xl shadow-md p-8 h-full flex items-center justify-center">
        <p className="text-gray-400 text-center">No data available</p>
      </div>
    );
  }

  const stats = sensorData.stats;
  const frequencies = sensorData.frequencies || [];
  const amplitudes = sensorData.amplitudes || [];
  
  let paramValue = 0;
  let paramLabel = selectedParam;

  // Get value based on parameter type (unchanged logic)
  if (selectedParam.startsWith('frequency')) {
    const idx = parseInt(selectedParam.replace('frequency', '')) - 1;
    paramValue = frequencies[idx] || 0;
    paramLabel = `Frequency ${idx + 1}`;
  } else if (selectedParam.startsWith('amplitude')) {
    const idx = parseInt(selectedParam.replace('amplitude', '')) - 1;
    paramValue = amplitudes[idx] || 0;
    paramLabel = `Amplitude ${idx + 1}`;
  } else {
    paramValue = stats[selectedParam] || 0;
  }

  const timeWindows = ['10-12', '12-14', '14-16', '16-18', '18-20'];
  
  // Generate realistic 2-hour window data (unchanged logic)
  const windowData = timeWindows.map((_, idx) => {
    const variance = 0.8 + Math.random() * 0.4;
    return Number((paramValue * variance).toFixed(4));
  });

  const chartData = {
    labels: timeWindows,
    datasets: [
      {
        label: `${paramLabel} - 2hr Windows`,
        data: windowData,
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 5,
        pointBackgroundColor: '#10b981',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointHoverRadius: 7
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: true,
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

  return (
    <div className="bg-white rounded-xl shadow-md p-8 flex flex-col h-full">
      {/* Card Header */}
      <div className="mb-6 pb-4 border-b-2 border-gray-100">
        <h2 className="text-xl font-bold text-gray-900 mb-3">Statistical Trend Analysis</h2>
        <p className="text-sm text-gray-600 font-medium">Parameter: <span className="text-blue-600 font-semibold">{paramLabel}</span></p>
      </div>

      {/* Chart Container */}
      <div style={{ height: '320px', flex: 1 }} className="relative">
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
      <div className="bg-white rounded-xl shadow-md p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-3">File Upload History</h3>
        <p className="text-sm text-gray-500 text-center py-8">No files found for {sensor}</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden">
      {/* Card Header */}
      <div className="bg-gradient-to-r from-gray-50 to-gray-100 px-6 py-4 border-b-2 border-gray-200">
        <h3 className="text-lg font-bold text-gray-900">File Upload History</h3>
        <p className="text-xs text-gray-600 mt-1">Latest 10 uploads (5 pairs)</p>
      </div>

      {/* Table Container with Scroll */}
      <div className="overflow-y-auto max-h-64">
        <table className="w-full">
          <tbody>
            {files.map((file, idx) => (
              <tr key={idx} className={idx % 2 === 0 ? 'bg-gray-50' : 'bg-white hover:bg-gray-100 transition'}>
                <td className="px-6 py-4 border-b border-gray-200 text-xs">
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-600 text-xs font-semibold">
                        {idx + 1}
                      </span>
                      <span className="font-semibold text-gray-800">{file.timestamp}</span>
                    </div>
                    <div className="text-gray-600 ml-8">
                      <div className="truncate">📄 {file.maxFile}</div>
                      <div className="truncate">📄 {file.minFile}</div>
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
    <div className="bg-white rounded-xl shadow-md overflow-hidden flex flex-col">
      {/* Card Header */}
      <div className="bg-gradient-to-r from-blue-50 to-blue-100 px-6 py-5 border-b-2 border-blue-200">
        <h3 className="text-lg font-bold text-gray-900 mb-1">Statistical Analysis Table</h3>
        <p className="text-xs text-gray-700">
          Sensor: <span className="font-semibold text-blue-600 capitalize">{selectedSensor}</span> • 
          Mode: <span className="font-semibold text-blue-600 uppercase">{mode}</span>
        </p>
      </div>

      {/* Scrollable Table Container */}
      <div className="overflow-y-auto flex-1 max-h-96">
        <table className="w-full text-sm">
          <thead className="bg-gray-100 border-b-2 border-gray-300 sticky top-0 z-10">
            <tr>
              <th className="px-5 py-3 text-left font-bold text-gray-800 whitespace-nowrap">Parameter</th>
              <th className="px-5 py-3 text-right font-bold text-gray-800 whitespace-nowrap">Value</th>
            </tr>
          </thead>
          <tbody>
            {parameters.map((param, idx) => {
              // Group parameters visually
              const isFrequency = param.key.startsWith('frequency');
              const isAmplitude = param.key.startsWith('amplitude');
              const bgClass = isFrequency ? 'bg-blue-50' : isAmplitude ? 'bg-green-50' : idx % 2 === 0 ? 'bg-white' : 'bg-gray-50';
              const hoverClass = 'hover:bg-opacity-75 transition';

              return (
                <tr key={param.key} className={`${bgClass} ${hoverClass} border-b border-gray-200`}>
                  <td className="px-5 py-3 font-semibold text-gray-800">{param.label}</td>
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
    } catch (err) {
      console.error('Error fetching file history:', err);
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
    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchSensorData(mode);
      }, 5000);
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

  const currentSensorData = sensorData[selectedSensor] || {};

  // ============================================================
  // RENDER - Professional Industrial Dashboard Layout
  // ============================================================
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* HEADER SECTION - Professional Title Bar */}
      <header className="bg-slate-950 border-b-2 border-slate-700 shadow-xl sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            {/* Left: Title and Subtitle */}
            <div className="flex-1">
              <h1 className="text-3xl md:text-4xl font-black text-white tracking-tight">
                ⚙️ Predictive Maintenance Dashboard
              </h1>
              <p className="text-slate-400 text-sm md:text-base mt-1 font-medium">
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
                className="h-12 px-5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition duration-200 flex items-center gap-2 shadow-lg hover:shadow-xl transform hover:scale-105"
              >
                <span>🔄</span>
                <span className="hidden sm:inline">Refresh</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* CONTROLS SECTION - Global Settings */}
      <div className="bg-slate-800 border-b border-slate-700 px-6 py-4 shadow-md">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col sm:flex-row gap-6 items-start sm:items-center">
            {/* View Mode Selector */}
            <div className="w-full sm:w-auto">
              <label className="block text-slate-300 text-sm font-bold uppercase tracking-wider mb-2">
                Monitoring Mode
              </label>
              <select
                value={mode}
                onChange={handleModeChange}
                className="w-full h-12 bg-slate-700 text-white border-2 border-slate-600 rounded-lg px-4 py-2 font-semibold hover:border-blue-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-400 focus:outline-none transition duration-200 cursor-pointer appearance-none bg-no-repeat bg-right-4 pr-10"
                style={{
                  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%93c5fd' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E")`,
                }}
              >
                {MODES.map(m => (
                  <option key={m.value} value={m.value} className="bg-slate-700 text-white">
                    {m.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Auto-Refresh Toggle */}
            <div className="flex items-center gap-3 pt-4 sm:pt-0">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-12 h-7 bg-slate-600 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-blue-600"></div>
                <span className="ml-3 text-slate-300 font-semibold">Auto-refresh (5s)</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* ERROR DISPLAY */}
      {error && (
        <div className="mx-6 mt-6 bg-red-900 border-l-4 border-red-600 text-red-100 p-4 rounded-lg shadow-lg max-w-7xl mx-auto">
          <p className="font-bold flex items-center gap-2">
            <span>⚠️</span> Error: {error}
          </p>
        </div>
      )}

      {/* LOADING STATE */}
      {loading && Object.keys(sensorData).length === 0 && (
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mb-4"></div>
            <p className="text-slate-400 text-lg font-semibold">Loading sensor data...</p>
          </div>
        </div>
      )}

      {/* MAIN DASHBOARD GRID - 30/70 Layout */}
      {!loading && Object.keys(sensorData).length > 0 && (
        <main className="max-w-7xl mx-auto px-6 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 auto-rows-max lg:auto-rows-min">
            {/* ================================================
                LEFT SIDEBAR (30% width) - Sensor Controls & Data
                ================================================ */}
            <div className="lg:col-span-1 space-y-6">
              {/* SENSOR SELECTION CARD */}
              <div className="bg-white rounded-xl shadow-md overflow-hidden">
                <div className="bg-gradient-to-r from-blue-50 to-blue-100 px-6 py-4 border-b-2 border-blue-200">
                  <h2 className="text-lg font-bold text-gray-900">Sensor Selection</h2>
                  <p className="text-xs text-gray-700 mt-1">Choose sensor for detailed analysis</p>
                </div>
                <div className="p-6">
                  <select
                    value={selectedSensor}
                    onChange={handleSensorChange}
                    className="w-full h-12 bg-gray-50 text-gray-900 border-2 border-gray-300 rounded-lg px-4 py-3 font-semibold hover:border-blue-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 focus:outline-none transition duration-200 cursor-pointer appearance-none bg-no-repeat bg-right-4 pr-10"
                    style={{
                      backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%236B7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E")`,
                    }}
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

              {/* STATISTICS TABLE CARD */}
              <div className="h-full">
                <EnhancedStatisticsTable
                  sensorData={sensorData}
                  selectedSensor={selectedSensor}
                  mode={mode}
                />
              </div>
            </div>

            {/* ================================================
                RIGHT CONTENT AREA (70% width) - Charts & Analysis
                ================================================ */}
            <div className="lg:col-span-2 space-y-6">
              {/* TIME SERIES CHART CARD */}
              <div className="bg-white rounded-xl shadow-md overflow-hidden h-96">
                <TimeSeriesChart 
                  sensor={timeSeriesSensor} 
                  sensorData={sensorData[timeSeriesSensor] || {}}
                  onSensorChange={handleTimeSeriesSensorChange}
                />
              </div>

              {/* STATISTICAL TREND ANALYSIS CARD */}
              <div className="bg-white rounded-xl shadow-md overflow-hidden">
                {/* Parameter Selector Header */}
                <div className="bg-gradient-to-r from-emerald-50 to-emerald-100 px-8 py-5 border-b-2 border-emerald-200">
                  <h2 className="text-lg font-bold text-gray-900 mb-3">Statistical Trend Analysis</h2>
                  <div className="w-full">
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Select Parameter:</label>
                    <select
                      value={selectedParam}
                      onChange={handleParamChange}
                      className="w-full h-12 bg-gray-50 text-gray-900 border-2 border-gray-300 rounded-lg px-4 py-3 font-medium hover:border-emerald-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 focus:outline-none transition duration-200 cursor-pointer appearance-none bg-no-repeat bg-right-4 pr-10"
                      style={{
                        backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%236B7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E")`,
                      }}
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
                <div className="p-8">
                  <div style={{ height: '320px' }} className="relative">
                    <StatisticalAnalysisChart
                      sensor={timeSeriesSensor}
                      sensorData={sensorData[timeSeriesSensor] || {}}
                      selectedParam={selectedParam}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      )}
    </div>
  );
}

export default App;
