import { useEffect, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import './index.css';

const API_BASE_URL = 'https://wilo-cloud-monitoring.onrender.com';
const SENSORS = ['acceleration', 'current', 'audio'];
const MODES = [
  { value: 'max', label: 'MAX View' },
  { value: 'min', label: 'MIN View' },
  { value: 'combined', label: 'COMBINED View' }
];

// Health status color mapping
const HEALTH_COLORS = {
  normal: { bg: 'bg-green-50', border: 'border-green-300', text: 'text-green-700', badge: 'bg-green-500' },
  warning: { bg: 'bg-yellow-50', border: 'border-yellow-300', text: 'text-yellow-700', badge: 'bg-yellow-500' },
  critical: { bg: 'bg-red-50', border: 'border-red-300', text: 'text-red-700', badge: 'bg-red-500' },
  unknown: { bg: 'bg-gray-50', border: 'border-gray-300', text: 'text-gray-700', badge: 'bg-gray-500' }
};

function SensorCard({ sensor, data }) {
  const health = data?.health || 'unknown';
  const colors = HEALTH_COLORS[health];
  const stats = data?.stats || {};
  
  return (
    <div className={`rounded-lg border-2 p-6 ${colors.border} ${colors.bg}`}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold capitalize">{sensor}</h2>
        <span className={`${colors.badge} text-white px-4 py-1 rounded-full text-sm font-semibold capitalize`}>
          {health}
        </span>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white bg-opacity-60 p-3 rounded">
          <p className="text-xs text-gray-600">Mean</p>
          <p className="text-lg font-semibold">{stats.mean?.toFixed(3) || '-'}</p>
        </div>
        <div className="bg-white bg-opacity-60 p-3 rounded">
          <p className="text-xs text-gray-600">Max</p>
          <p className="text-lg font-semibold">{stats.max?.toFixed(3) || '-'}</p>
        </div>
        <div className="bg-white bg-opacity-60 p-3 rounded">
          <p className="text-xs text-gray-600">Min</p>
          <p className="text-lg font-semibold">{stats.min?.toFixed(3) || '-'}</p>
        </div>
        <div className="bg-white bg-opacity-60 p-3 rounded">
          <p className="text-xs text-gray-600">Std Dev</p>
          <p className="text-lg font-semibold">{stats.std_dev?.toFixed(3) || '-'}</p>
        </div>
      </div>
    </div>
  );
}

function StatisticsTable({ sensorData, mode }) {
  const parameters = [
    { key: 'mean', label: 'Mean' },
    { key: 'max', label: 'Max' },
    { key: 'min', label: 'Min' },
    { key: 'std_dev', label: 'Standard Deviation' },
    { key: 'range', label: 'Range' },
    { key: 'skewness', label: 'Skewness' },
    { key: 'kurtosis', label: 'Kurtosis' }
  ];
  
  return (
    <div className="bg-white rounded-lg shadow-lg p-6 mt-8">
      <h2 className="text-2xl font-bold mb-2">Statistical Analysis</h2>
      <p className="text-gray-600 mb-4 text-sm">View Mode: <span className="font-semibold uppercase">{mode}</span></p>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-100 border-b-2 border-gray-300">
            <tr>
              <th className="px-4 py-3 text-left font-semibold">Parameter</th>
              {SENSORS.map(sensor => (
                <th key={sensor} className="px-4 py-3 text-center font-semibold capitalize">{sensor}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {parameters.map((param, idx) => (
              <tr key={param.key} className={idx % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                <td className="px-4 py-3 font-medium border-b border-gray-200">{param.label}</td>
                {SENSORS.map(sensor => (
                  <td key={`${sensor}-${param.key}`} className="px-4 py-3 text-center border-b border-gray-200">
                    {sensorData[sensor]?.stats[param.key]?.toFixed(4) || '-'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FFTSpectrumChart({ sensor, frequencies, amplitudes }) {
  if (!frequencies || frequencies.length === 0 || !amplitudes || amplitudes.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="font-semibold capitalize mb-4">{sensor} - FFT Spectrum</h3>
        <p className="text-gray-500">No frequency data available</p>
      </div>
    );
  }

  // Prepare data for bar chart
  const chartData = frequencies.map((freq, idx) => ({
    name: `${freq.toFixed(1)} Hz`,
    frequency: parseFloat(freq.toFixed(2)),
    amplitude: parseFloat((amplitudes[idx] || 0).toFixed(4))
  }));

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h3 className="font-semibold capitalize mb-4">{sensor} - FFT Spectrum (Top 5 Frequencies)</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="name" 
            angle={-45}
            textAnchor="end"
            height={100}
            interval={0}
          />
          <YAxis label={{ value: 'Amplitude', angle: -90, position: 'insideLeft' }} />
          <Tooltip 
            formatter={(value) => value.toFixed(4)}
            labelFormatter={(label) => `${label}`}
          />
          <Bar dataKey="amplitude" fill="#3b82f6" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <div className="mt-4 p-3 bg-gray-50 rounded text-sm">
        <p className="text-gray-700">
          <strong>Max Amplitude:</strong> {Math.max(...amplitudes).toFixed(4)} at{' '}
          <strong>{frequencies[amplitudes.indexOf(Math.max(...amplitudes))].toFixed(2)} Hz</strong>
        </p>
      </div>
    </div>
  );
}

function FrequencyListTable({ sensor, frequencies, amplitudes }) {
  if (!frequencies || frequencies.length === 0 || !amplitudes || amplitudes.length === 0) {
    return null;
  }

  return (
    <div className="bg-gray-50 rounded-lg p-4 mt-4">
      <h4 className="font-semibold mb-3 text-sm">Frequency Components</h4>
      <table className="w-full text-sm">
        <thead className="bg-gray-200 border-b">
          <tr>
            <th className="px-3 py-2 text-left">Rank</th>
            <th className="px-3 py-2 text-left">Frequency (Hz)</th>
            <th className="px-3 py-2 text-right">Amplitude</th>
            <th className="px-3 py-2 text-right">% of Max</th>
          </tr>
        </thead>
        <tbody>
          {frequencies.map((freq, idx) => {
            const maxAmp = Math.max(...amplitudes);
            const percentage = maxAmp > 0 ? ((amplitudes[idx] / maxAmp) * 100).toFixed(1) : 0;
            return (
              <tr key={idx} className="border-b hover:bg-gray-100">
                <td className="px-3 py-2">{idx + 1}</td>
                <td className="px-3 py-2 font-mono">{freq.toFixed(2)}</td>
                <td className="px-3 py-2 text-right font-mono">{amplitudes[idx].toFixed(4)}</td>
                <td className="px-3 py-2 text-right">{percentage}%</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function App() {
  const [sensorData, setSensorData] = useState({});
  const [mode, setMode] = useState('max');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

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

  // Fetch data when mode changes
  useEffect(() => {
    fetchSensorData(mode);
  }, [mode]);

  // Auto-refresh interval
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchSensorData(mode);
      }, 2 * 60 * 60 * 1000); // Refresh every 2 hours
      return () => clearInterval(interval);
    }
  }, [autoRefresh, mode]);

  const handleModeChange = (e) => {
    const newMode = e.target.value;
    setMode(newMode);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">Predictive Maintenance</h1>
            <p className="text-gray-400">Real-time sensor monitoring and analysis with FFT spectrum visualization</p>
          </div>
          <div className="text-right">
            <p className="text-gray-400 text-sm">Last updated: <span className="text-green-400 font-semibold">{lastUpdate || 'Never'}</span></p>
            <button
              onClick={() => fetchSensorData(mode)}
              className="mt-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition"
            >
              🔄 Refresh Now
            </button>
          </div>
        </div>

        {/* Controls */}
        <div className="flex gap-6 items-center">
          <div className="flex items-center gap-3">
            <label className="text-white font-semibold">View Mode:</label>
            <select
              value={mode}
              onChange={handleModeChange}
              className="bg-gray-700 text-white border-2 border-gray-600 rounded-lg px-4 py-2 font-semibold hover:border-blue-500 transition cursor-pointer"
            >
              {MODES.map(m => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>
          
          <label className="flex items-center gap-2 text-white cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="w-4 h-4"
            />
            <span>Auto-refresh every 2h</span>
          </label>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="max-w-7xl mx-auto mb-6 bg-red-900 border border-red-700 rounded-lg p-4 text-red-100">
          ⚠️ Error: {error}
        </div>
      )}

      {loading && Object.keys(sensorData).length === 0 ? (
        <div className="max-w-7xl mx-auto text-center text-gray-400">
          <p className="text-lg">Loading sensor data for {mode.toUpperCase()} mode...</p>
        </div>
      ) : (
        <>
          {/* Sensor Cards */}
          <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {SENSORS.map(sensor => (
              <SensorCard
                key={sensor}
                sensor={sensor}
                data={sensorData[sensor] || {}}
              />
            ))}
          </div>

          {/* Statistics Table */}
          <div className="max-w-7xl mx-auto">
            <StatisticsTable sensorData={sensorData} mode={mode} />
          </div>

          {/* FFT Spectrum Charts */}
          <div className="max-w-7xl mx-auto mt-8 mb-8">
            <h2 className="text-3xl font-bold text-white mb-6">FFT Frequency Spectrum Analysis</h2>
            <div className="grid grid-cols-1 gap-8">
              {SENSORS.map(sensor => (
                <div key={`fft-${sensor}`} className="bg-white rounded-lg shadow-lg overflow-hidden">
                  <FFTSpectrumChart
                    sensor={sensor}
                    frequencies={sensorData[sensor]?.frequencies || []}
                    amplitudes={sensorData[sensor]?.amplitudes || []}
                  />
                  <FrequencyListTable
                    sensor={sensor}
                    frequencies={sensorData[sensor]?.frequencies || []}
                    amplitudes={sensorData[sensor]?.amplitudes || []}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Data Points Info */}
          <div className="max-w-7xl mx-auto bg-gray-800 rounded-lg p-6 text-gray-300">
            <h3 className="text-lg font-semibold mb-4">Data Summary ({mode.toUpperCase()} Mode)</h3>
            <div className="grid grid-cols-3 gap-6">
              {SENSORS.map(sensor => (
                <div key={`info-${sensor}`}>
                  <p className="text-sm text-gray-400 capitalize">{sensor}</p>
                  <p className="text-2xl font-bold text-blue-400">{sensorData[sensor]?.data_points || 0}</p>
                  <p className="text-xs text-gray-500">data points analyzed</p>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default App;
