import { Outlet } from 'react-router-dom';
import Navbar from './components/Navbar';
import ConnectionBackground from './components/ConnectionBackground';

export default function App() {
  return (
    <div className="app">
      <ConnectionBackground />
      <Navbar />
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
