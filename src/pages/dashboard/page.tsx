import { useEffect, useState } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import DashboardOverview from './components/DashboardOverview';
import SalesList from './components/SalesList';
import Reports from './components/Reports';
import Analytics from './components/Analytics';
import Settings from './components/Settings';
import Export from './components/Export';
import DailySalesInput from './components/DailySalesInput';
import CsvImport from './components/CsvImport';
import { DailySalesEntry, dailySalesEntries } from '../../mocks/dailySalesData';

const STORAGE_KEY = 'salespos.dailySalesEntries.v1';

const loadEntriesFromStorage = (): DailySalesEntry[] => {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return dailySalesEntries;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return dailySalesEntries;
    return parsed;
  } catch {
    return dailySalesEntries;
  }
};

const Dashboard = () => {
  const [activeSection, setActiveSection] = useState('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [entries, setEntries] = useState<DailySalesEntry[]>(loadEntriesFromStorage);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  }, [entries]);

  const renderContent = () => {
    switch (activeSection) {
      case 'dashboard':
        return <DashboardOverview />;
      case 'daily-input':
        return <DailySalesInput entries={entries} setEntries={setEntries} />;
      case 'csv-import':
        return <CsvImport setEntries={setEntries} />;
      case 'sales':
        return <SalesList />;
      case 'reports':
        return <Reports />;
      case 'analytics':
        return <Analytics />;
      case 'settings':
        return <Settings />;
      case 'export':
        return <Export />;
      default:
        return <DashboardOverview />;
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar 
        activeSection={activeSection} 
        setActiveSection={setActiveSection}
        isOpen={sidebarOpen}
        setIsOpen={setSidebarOpen}
      />
      <div className={`flex-1 flex flex-col overflow-hidden transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-20'}`}>
        <Header toggleSidebar={() => setSidebarOpen(!sidebarOpen)} />
        <main className="flex-1 overflow-y-auto p-6">
          {renderContent()}
        </main>
      </div>
    </div>
  );
};

export default Dashboard;
