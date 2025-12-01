export default function ScreenshotPreview({ screenshot }) {
    if (!screenshot) return null;
  
    return (
      <div style={{ marginTop: "20px" }}>
        <h3>Cropped Preview:</h3>
        <img
          src={screenshot}
          alt="cropped"
          style={{
            maxWidth: "400px",
            border: "2px solid #333",
            borderRadius: "4px",
          }}
        />
      </div>
    );
  }
  