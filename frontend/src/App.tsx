import { BrowserRouter, Routes, Route } from "react-router-dom";
import MapPage from "./pages/MapPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MapPage />} />
      </Routes>
    </BrowserRouter>
  );
}
