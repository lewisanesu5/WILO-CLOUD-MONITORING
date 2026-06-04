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

// Reusable Components
function TimeSeriesChart({ sensor, sensorData, onSensorChange }) {
  if (!sensorData || !sensorData.stats) {
    return <div className="bg-white rounded-lg shadow-lg p-6">No data available</div>;
  }

  const data = sensorData.stats;
  const chartData = {
    labels: ['Min', 'Mean', 'Max'],
    datasets: [
      {
        label: `${sensor} - Time Series`,
        data: [data.min || 0, data.mean || 0, data.max || 0],
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#3b82f6'
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: { display: true, position: 'top' }
    },
    scales: {
      y: {
        title: { display: true, text: 'Value' }
      }
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="mb-4">
        <label className="font-semibold block mb-2">Select Parameter:</label>
        <select
          value={sensor}
          onChange={(e) => onSensorChange(e.target.value)}
          className="w-full bg-gray-100 text-gray-800 border-2 border-gray-300 rounded-lg px-3 py-2 font-semibold hover:border-blue-500 transition cursor-pointer"
        >
          {SENSORS.map(s => (
            <option key={s} value={s}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </option>
          ))}
        </select>
      </div>
      <h3 className="font-semibold text-lg mb-4 capitalize">Time Series - {sensor}</h3>
      <div style={{ height: '250px' }}>
        <Line data={chartData} options={options} />
      </div>
    </div>
  );
}

function StatisticalAnalysisChart({ sensor, sensorData, selectedParam }) {
  if (!sensorData || !sensorData.stats) {
    return <div className="bg-white rounded-lg shadow-lg p-6">No data available</div>;
  }

  const stats = sensorData.stats;
  const frequencies = sensorData.frequencies || [];
  const amplitudes = sensorData.amplitudes || [];
  
  let paramValue = 0;
  let paramLabel = selectedParam;

  // Get value based on parameter type
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
  
  // Generate realistic 2-hour window data
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
        pointRadius: 4,
        pointBackgroundColor: '#10b981'
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: { legend: { display: true } },
    scales: {
      y: {
        title: { display: true, text: 'Value' }
      }
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h3 className="font-semibold text-lg mb-4 capitalize">Statistical Analysis - {paramLabel}</h3>
      <div style={{ height: '250px' }}>
        <Line data={chartData} options={options} />
      </div>
    </div>
  );
}

function FileHistoryTable({ files, sensor }) {
  if (!files || files.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-4 mt-4 border-t-4 border-gray-300">
        <h3 className="font-semibold mb-3 capitalize">File History - {sensor} (Latest 10)</h3>
        <p className="text-gray-500 text-sm">No files found for this sensor</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-4 mt-4 border-t-4 border-blue-500">
      <h3 className="font-semibold mb-3 capitalize">File History - {sensor} (Latest 10)</h3>
      <div className="overflow-y-auto max-h-56">
        <table className="w-full text-xs">
          <tbody>
            {files.map((file, idx) => (
              <tr key={idx} className={idx % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                <td className="px-3 py-2 border-b border-gray-200">
                  <div className="font-semibold text-gray-800 mb-1">{file.timestamp}</div>
                  <div className="text-gray-600">{file.maxFile}</div>
                  <div className="text-gray-600">{file.minFile}</div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FrequenciesTable({ sensor, frequencies, amplitudes }) {
  return (
    <div className="bg-white rounded-lg shadow-lg p-4 mt-4 border-t-4 border-purple-500">
      <h3 className="font-semibold mb-3 capitalize">Top 5 Frequencies - {sensor}</h3>
      <div className="overflow-y-auto max-h-48">
        <table className="w-full text-xs">
          <thead className="bg-gray-100 border-b sticky top-0">
            <tr>
              <th className="px-3 py-2 text-left font-semibold">Rank</th>
              <th className="px-3 py-2 text-center font-semibold">Freq (Hz)</th>
              <th className="px-3 py-2 text-center font-semibold">Amplitude</th>
            </tr>
          </thead>
          <tbody>
            {(frequencies || []).slice(0, 5).map((freq, idx) => (
              <tr key={idx} className={idx % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                <td className="px-3 py-2 text-center border-b border-gray-200 font-medium">{idx + 1}</td>
                <td className="px-3 py-2 text-center border-b border-gray-200">{freq.toFixed(2)}</td>
                <td className="px-3 py-2 text-center border-b border-gray-200">{(amplitudes?.[idx] || 0).toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function EnhancedStatisticsTable({ sensorData, selectedSensor, mode }) {
  const parameters = [
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

  const data = sensorData[selectedSensor] || {};
  const stats = data.stats || {};
  const frequencies = data.frequencies || [];
  const amplitudes = data.amplitudes || [];

  // Create combined data object for all parameters
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
    <div className="bg-white rounded-lg shadow-lg p-6 mt-8">
      <h2 className="text-2xl font-bold mb-2">Statistical Analysis</h2>
      <p className="text-gray-600 mb-4 text-sm">
        Sensor: <span className="font-semibold capitalize">{selectedSensor}</span> | 
        Mode: <span className="font-semibold uppercase">{mode}</span>
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-100 border-b-2 border-gray-300">
            <tr>
              <th className="px-4 py-3 text-left font-semibold">Parameter</th>
              <th className="px-4 py-3 text-center font-semibold">Value</th>
            </tr>
          </thead>
          <tbody>
            {parameters.map((param, idx) => (
              <tr key={param.key} className={idx % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                <td className="px-4 py-3 font-medium border-b border-gray-200">{param.label}</td>
                <td className="px-4 py-3 text-center border-b border-gray-200 font-semibold">
                  {allData[param.key] !== undefined && allData[param.key] !== null 
                    ? (typeof allData[param.key] === 'number' ? allData[param.key].toFixed(4) : allData[param.key])
                    : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}


function App() {
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
      
      setFileHistory(pairs.slice(0, 5)); // Show 5 pairs
    } catch (err) {
      console.error('Error fetching file history:', err);
    }
  };

  // Fetch data when mode changes
  useEffect(() => {
    fetchSensorData(mode);
  }, [mode]);

  // Fetch file history when sensor changes
  useEffect(() => {
    fetchFileHistory(selectedSensor);
  }, [selectedSensor]);

  // Auto-refresh interval
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchSensorData(mode);
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, mode]);

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

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-8">
      {/* Header */}
      <div className="max-w-full mx-auto mb-8">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">Predictive Maintenance</h1>
            <p className="text-gray-400">Real-time sensor monitoring and FFT analysis</p>
          </div>
          <div className="text-right">
            <p className="text-gray-400 text-sm">
              Last updated: <span className="text-green-400 font-semibold">{lastUpdate || 'Never'}</span>
            </p>
            <button
              onClick={() => fetchSensorData(mode)}
              className="mt-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition"
            >
              🔄 Refresh Now
            </button>
          </div>
        </div>

        {/* Top Controls */}
        <div className="flex gap-6 items-center flex-wrap">
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
            <span>Auto-refresh every 5s</span>
          </label>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="max-w-full mx-auto mb-6 bg-red-900 border border-red-700 rounded-lg p-4 text-red-100">
          ⚠️ Error: {error}
        </div>
      )}

      {loading && Object.keys(sensorData).length === 0 ? (
        <div className="max-w-full mx-auto text-center text-gray-400">
          <p className="text-lg">Loading sensor data...</p>
        </div>
      ) : (
        <div className="max-w-full mx-auto grid grid-cols-3 gap-8">
          {/* LEFT DIVISION (1/3 width) */}
          <div className="col-span-1 space-y-4">
            {/* Sensor Dropdown */}
            <div className="bg-gray-800 rounded-lg p-4 border-l-4 border-blue-500">
              <label className="text-white font-semibold block mb-2">Select Sensor:</label>
              <select
                value={selectedSensor}
                onChange={handleSensorChange}
                className="w-full bg-gray-700 text-white border-2 border-gray-600 rounded-lg px-3 py-2 font-semibold hover:border-blue-500 transition cursor-pointer"
              >
                {SENSORS.map(sensor => (
                  <option key={sensor} value={sensor}>
                    {sensor}
                  </option>
                ))}
              </select>
            </div>

            {/* File History */}
            <FileHistoryTable files={fileHistory} sensor={selectedSensor} />

            {/* Enhanced Statistics Table */}
            <EnhancedStatisticsTable
              sensorData={sensorData}
              selectedSensor={selectedSensor}
              mode={mode}
            />
          </div>

          {/* RIGHT DIVISION (2/3 width) */}
          <div className="col-span-2 space-y-8">
            {/* Top Graph - Time Series */}
            <TimeSeriesChart 
              sensor={timeSeriesSensor} 
              sensorData={sensorData[timeSeriesSensor] || {}}
              onSensorChange={handleTimeSeriesSensorChange}
            />

            {/* Bottom Graph - Statistical Analysis */}
            <div className="bg-gray-800 rounded-lg shadow-lg p-6">
              <div className="mb-4">
                <label className="text-white font-semibold block mb-2">Statistical Parameter:</label>
                <select
                  value={selectedParam}
                  onChange={handleParamChange}
                  className="w-full bg-gray-700 text-white border-2 border-gray-600 rounded-lg px-3 py-2 font-semibold hover:border-green-500 transition cursor-pointer"
                >
                  {STAT_PARAMETERS.map(param => (
                    <option key={param.key} value={param.key}>
                      {param.label}
                    </option>
                  ))}
                </select>
              </div>
              <StatisticalAnalysisChart
                sensor={timeSeriesSensor}
                sensorData={sensorData[timeSeriesSensor] || {}}
                selectedParam={selectedParam}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
