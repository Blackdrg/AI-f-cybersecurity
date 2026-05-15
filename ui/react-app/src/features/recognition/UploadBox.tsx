import React, { useState, DragEvent, ChangeEvent } from 'react';
import { Box, Typography, Button, Paper } from '@mui/material';
import { CloudUpload } from '@mui/icons-material';

interface UploadBoxProps {
  onUpload: (file: File) => void;
  isProcessing: boolean;
}

const UploadBox = ({ onUpload, isProcessing }: UploadBoxProps) => {
  const [dragActive, setDragActive] = useState<boolean>(false);

  const handleDrag = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file: File = e.dataTransfer.files[0];
    if (file) {
      onUpload(file);
    }
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    const file: File = e.target.files?.[0] as File;
    if (file) {
      onUpload(file);
    }
  };

  return (
    <Paper
      variant="outlined"
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      sx={{
        p: 4,
        textAlign: 'center',
        borderStyle: 'dashed',
        borderWidth: 2,
        borderColor: dragActive ? 'primary.main' : 'divider',
        bgcolor: dragActive ? 'rgba(0, 188, 212, 0.05)' : 'transparent',
        transition: 'all 0.3s ease',
        cursor: 'pointer'
      }}
    >
      <input
        accept="image/*"
        style={{ display: 'none' }}
        id="raised-button-file"
        type="file"
        onChange={handleChange}
        disabled={isProcessing}
      />
      <label htmlFor="raised-button-file">
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <CloudUpload sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Drag and drop or click to upload
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Supported formats: JPG, PNG, WEBP
          </Typography>
          <Button variant="contained" component="span" disabled={isProcessing}>
            Select Image
          </Button>
        </Box>
      </label>
    </Paper>
  );
};

export default UploadBox;



