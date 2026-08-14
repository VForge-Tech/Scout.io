import DashboardLayout from '../../components/DashboardLayout';

export default function DashboardTeam() {
  return (
    <DashboardLayout>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Team</h2>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm">
          Invite Member
        </button>
      </div>
      <div className="bg-white rounded-lg shadow">
        <p className="p-8 text-center text-gray-500">Team management coming soon</p>
      </div>
    </DashboardLayout>
  );
}