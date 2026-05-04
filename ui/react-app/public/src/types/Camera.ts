export interface Camera {
  id: string;
  name: string;
  rtsp_url: string;
  location?: string;
  status: 'active' | 'inactive' | 'error';
  org_id?: string;
}

