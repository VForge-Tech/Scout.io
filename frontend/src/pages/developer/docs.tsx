import DeveloperLayout from '../../components/DeveloperLayout';

export default function ApiDocs() {
  return (
    <DeveloperLayout>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">API Documentation</h2>
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-600 mb-4">
          Scout.io provides a RESTful API for integrating with your applications.
        </p>

        <h3 className="text-lg font-medium text-gray-900 mt-6 mb-2">Base URL</h3>
        <code className="block bg-gray-50 p-3 rounded text-sm font-mono">
          {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}
        </code>

        <h3 className="text-lg font-medium text-gray-900 mt-6 mb-2">Authentication</h3>
        <p className="text-gray-600 mb-2">
          Use Bearer token authentication with your API key:
        </p>
        <code className="block bg-gray-50 p-3 rounded text-sm font-mono">
          X-API-Key: sco_your_api_key_here
        </code>
        <p className="text-gray-500 text-sm mt-2">
          You can also use JWT Bearer tokens obtained from the login endpoint.
        </p>

        <h3 className="text-lg font-medium text-gray-900 mt-6 mb-2">Interactive Docs</h3>
        <p className="text-gray-600">
          Full interactive API documentation is available at:
        </p>
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:text-blue-800 mt-2 inline-block"
        >
          http://localhost:8000/docs →
        </a>
        <div className="mt-4">
          <a
            href="http://localhost:8000/redoc"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-800 inline-block"
          >
            http://localhost:8000/redoc →
          </a>
        </div>
      </div>
    </DeveloperLayout>
  );
}
