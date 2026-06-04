import { useEffect, useState } from 'react';
import './index.css';

const API_BASE_URL = 'https://wilo-cloud-monitoring.onrender.com';
const SENSORS = ['acceleration', 'current', 'audio'];

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

function StatisticsTable({ sensorData }) {
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
      <h2 className="text-2xl font-bold mb-4">Statistical Analysis</h2>
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

function FrequencyChart({ sensor, frequencies, amplitudes }) {
  if (!frequencies || frequencies.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="font-semibold capitalize mb-4">{sensor} - Frequencies</h3>
        <p className="text-gray-500">No frequency data available</p>
      </div>
    );
  }

  // Calculate max amplitude for scaling
  const maxAmp = Math.max(...amplitudes, 1);

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h3 className="font-semibold capitalize mb-4">{sensor} - Top 5 Frequencies</h3>
      <div className="space-y-3">
        {frequencies.map((freq, idx) => (
          <div key={idx} className="flex items-center gap-4">
            <div className="w-24">
              <p className="text-sm font-medium">{freq.toFixed(2)} Hz</p>
            </div>
            <div className="flex-1 bg-gray-200 rounded-full h-8 overflow-hidden">
              <div
                className="bg-gradient-to-r from-blue-400 to-blue-600 h-full flex items-center justify-end pr-2"
                style={{ width: `${(amplitudes[idx] / maxAmp) * 100}%` }}
              >
                {(amplitudes[idx] / maxAmp) * 100 > 15 && (
                  <span className="text-white text-xs font-semibold">{amplitudes[idx].toFixed(2)}</span>
                )}
              </div>
            </div>
            <div className="w-20 text-right text-sm text-gray-600">{amplitudes[idx].toFixed(2)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function App() {
  const [sensorData, setSensorData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchSensorData = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/sensor-data`);
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

  useEffect(() => {
    fetchSensorData();
    
    if (autoRefresh) {
      const interval = setInterval(fetchSensorData, 5000); // Refresh every 5 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">Predictive Maintenance</h1>
            <p className="text-gray-400">Real-time sensor monitoring and analysis</p>
          </div>
          <div className="text-right">
            <p className="text-gray-400 text-sm">Last updated: <span className="text-green-400 font-semibold">{lastUpdate || 'Never'}</span></p>
            <button
              onClick={fetchSensorData}
              className="mt-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition"
            >
              🔄 Refresh Now
            </button>
          </div>
        </div>

        {/* Controls */}
        <div className="flex gap-4">
          <label className="flex items-center gap-2 text-white cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="w-4 h-4"
            />
            <span>Auto-refresh every 5s</span>
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
          <p className="text-lg">Loading sensor data...</p>
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
            <StatisticsTable sensorData={sensorData} />
          </div>

          {/* Frequency Spectrum Charts */}
          <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6 mt-8 mb-8">
            {SENSORS.map(sensor => (
              <FrequencyChart
                key={`freq-${sensor}`}
                sensor={sensor}
                frequencies={sensorData[sensor]?.frequencies || []}
                amplitudes={sensorData[sensor]?.amplitudes || []}
              />
            ))}
          </div>

          {/* Data Points Info */}
          <div className="max-w-7xl mx-auto bg-gray-800 rounded-lg p-6 text-gray-300">
            <h3 className="text-lg font-semibold mb-4">Data Summary</h3>
            <div className="grid grid-cols-3 gap-6">
              {SENSORS.map(sensor => (
                <div key={`info-${sensor}`}>
                  <p className="text-sm text-gray-400 capitalize">{sensor}</p>
                  <p className="text-2xl font-bold text-blue-400">{sensorData[sensor]?.data_points || 0}</p>
                  <p className="text-xs text-gray-500">data points collected</p>
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
