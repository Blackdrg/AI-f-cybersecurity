export interface Camera {
  camera_id: string;
  org_id: string;
  name: string;
  rtsp_url: string;
  location?: string;
  status: 'online' | 'offline' | 'error';
  created_at: any;
}

