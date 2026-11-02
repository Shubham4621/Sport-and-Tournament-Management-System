const API_BASE_URL = (
  import.meta.env.VITE_API_URL || "http://127.0.0.1:5000/api"
).replace(/\/+$/, "");

function queryString(params = {}) {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== null),
  );
  return query.size ? `?${query}` : "";
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new Error(
      "Cannot reach the Flask API. Check that the backend is running at " +
        API_BASE_URL,
    );
  }

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : null;
  if (!response.ok) {
    throw new Error(
      payload?.error || `The API request failed with status ${response.status}.`,
    );
  }
  return payload;
}

export const api = {
  health: () => request("/health"),
  dashboardStats: () => request("/dashboard/stats"),
  sports: (params = {}) => request(`/sports${queryString(params)}`),
  sport: (id) => request(`/sports/${id}`),
  createSport: (sport) =>
    request("/sports", { method: "POST", body: JSON.stringify(sport) }),
  updateSport: (id, sport) =>
    request(`/sports/${id}`, { method: "PUT", body: JSON.stringify(sport) }),
  deleteSport: (id) => request(`/sports/${id}`, { method: "DELETE" }),
  departments: () => request("/departments"),
  teams: (params = {}) => request(`/teams${queryString(params)}`),
  team: (id, params = {}) => request(`/teams/${id}${queryString(params)}`),
  createTeam: (team) =>
    request("/teams", { method: "POST", body: JSON.stringify(team) }),
  updateTeam: (id, team) =>
    request(`/teams/${id}`, { method: "PUT", body: JSON.stringify(team) }),
  deleteTeam: (id) => request(`/teams/${id}`, { method: "DELETE" }),
  addTeamMember: (teamId, membership) =>
    request(`/teams/${teamId}/members`, {
      method: "POST",
      body: JSON.stringify(membership),
    }),
  removeTeamMember: (teamId, playerId) =>
    request(`/teams/${teamId}/members/${playerId}`, { method: "DELETE" }),
  students: (params = {}) => {
    return request(`/students${queryString(params)}`);
  },
  student: (id) => request(`/students/${id}`),
  createStudent: (student) =>
    request("/students", { method: "POST", body: JSON.stringify(student) }),
  updateStudent: (id, student) =>
    request(`/students/${id}`, {
      method: "PUT",
      body: JSON.stringify(student),
    }),
  deleteStudent: (id) => request(`/students/${id}`, { method: "DELETE" }),
  players: (params = {}) => request(`/players${queryString(params)}`),
  player: (id) => request(`/players/${id}`),
  createPlayer: (studentId, player = {}) =>
    request(`/students/${studentId}/player`, {
      method: "POST",
      body: JSON.stringify(player),
    }),
  playerEligibility: (playerId) =>
    request(`/players/${playerId}/eligibility`),
  addPlayerEligibility: (playerId, eligibility) =>
    request(`/players/${playerId}/eligibility`, {
      method: "POST",
      body: JSON.stringify(eligibility),
    }),
  updatePlayerEligibility: (playerId, sportId, eligibility) =>
    request(`/players/${playerId}/eligibility/${sportId}`, {
      method: "PUT",
      body: JSON.stringify(eligibility),
    }),
  endPlayerEligibility: (playerId, sportId) =>
    request(`/players/${playerId}/eligibility/${sportId}`, {
      method: "DELETE",
    }),
  tournaments: (params = {}) =>
    request(`/tournaments${queryString(params)}`),
  tournament: (id, params = {}) =>
    request(`/tournaments/${id}${queryString(params)}`),
  createTournament: (tournament) =>
    request("/tournaments", {
      method: "POST",
      body: JSON.stringify(tournament),
    }),
  updateTournament: (id, tournament) =>
    request(`/tournaments/${id}`, {
      method: "PUT",
      body: JSON.stringify(tournament),
    }),
  updateTournamentStatus: (id, status) =>
    request(`/tournaments/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  cancelTournament: (id) =>
    request(`/tournaments/${id}/cancel`, { method: "POST" }),
  tournamentRegistrations: (id, params = {}) =>
    request(`/tournaments/${id}/registrations${queryString(params)}`),
  registerTeam: (tournamentId, teamId) =>
    request(`/tournaments/${tournamentId}/teams`, {
      method: "POST",
      body: JSON.stringify({ team_id: teamId }),
    }),
  matches: (params = {}) => request(`/matches${queryString(params)}`),
  match: (id, params = {}) =>
    request(`/matches/${id}${queryString(params)}`),
  createMatch: (match) =>
    request("/matches", { method: "POST", body: JSON.stringify(match) }),
  updateMatch: (id, match) =>
    request(`/matches/${id}`, { method: "PUT", body: JSON.stringify(match) }),
  updateMatchStatus: (id, status) =>
    request(`/matches/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  matchParticipants: (id, params = {}) =>
    request(`/matches/${id}/participants${queryString(params)}`),
  saveMatchScores: (id, scores) =>
    request(`/matches/${id}/scores`, {
      method: "PUT",
      body: JSON.stringify({ scores }),
    }),
  declareMatchResults: (id, results, scores) =>
    request(`/matches/${id}/results`, {
      method: "PUT",
      body: JSON.stringify({ results, ...(scores ? { scores } : {}) }),
    }),
  matchResults: (id, params = {}) =>
    request(`/matches/${id}/results${queryString(params)}`),
  standings: (id) => request(`/tournaments/${id}/standings`),
  reportSummary: () => request("/reports/summary"),
  tournamentReport: (id, params = {}) =>
    request(`/reports/tournaments/${id}${queryString(params)}`),
  matchResultsReport: (params = {}) =>
    request(`/reports/match-results${queryString(params)}`),
  tournamentWinners: () => request("/reports/tournament-winners"),
};
