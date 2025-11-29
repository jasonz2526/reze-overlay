import React from "react";
import MangaOverlay from "./components/MangaOverlay/MangaOverlay";
import sampleJson from "./translated_output.json";

export default function App() {
  return (
    <div className="p-4">
      <h1 className="text-xl mb-3 font-bold">Manga Overlay Demo</h1>
      
      <MangaOverlay
        imageUrl={"/" + sampleJson.image_filename} 
        panels={sampleJson.panels}
        debug={true}
      />
    </div>
  );
}