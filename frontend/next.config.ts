import type { NextConfig } from 'next';

const config: NextConfig = {
  output: 'standalone',
  poweredByHeader: false,
  allowedDevOrigins: ['10.19.24.89'],
  async rewrites() {
    return [{ source: '/api/:path*', destination: `${process.env.API_INTERNAL_URL || 'http://api:8000'}/api/:path*` }];
  },
};
export default config;
