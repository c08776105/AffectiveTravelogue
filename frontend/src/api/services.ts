import { apiClient } from './client';
import type {
    RouteCreate, RouteResponse, RouteUpdate,
    WaypointCreate, WaypointResponse,
    EvaluationResponse, TravelogueResponse, TravelogueCreate
} from './types';

/**
 * This file is a wrapper around the FastAPI backend.
 * It provides a simple interface to interact with the backend, maintaining
 * contractual integrity with the OpenAPI spec.
 */
export const apiService = {
    /**
     * Create a new route.
     * @param data The data to create a route with.
     * @returns The created route.
     */
    createRoute: async (data: RouteCreate): Promise<RouteResponse> => {
        const response = await apiClient.post<RouteResponse>('/routes/', data);
        return response.data;
    },

    /**
     * List all routes.
     * @returns All routes ordered oldest-first.
     */
    listRoutes: async (): Promise<RouteResponse[]> => {
        const response = await apiClient.get<RouteResponse[]>('/routes/');
        return response.data;
    },

    /**
     * Get a route by its ID.
     * @param id The ID of the route to get.
     * @returns The route.
     */
    getRoute: async (id: string): Promise<RouteResponse> => {
        const response = await apiClient.get<RouteResponse>(`/routes/${id}`);
        return response.data;
    },

    /**
     * Update a route.
     * @param id The ID of the route to update.
     * @param data The data to update the route with.
     * @returns The updated route.
     */
    updateRoute: async (id: string, data: RouteUpdate): Promise<RouteResponse> => {
        const response = await apiClient.patch<RouteResponse>(`/routes/${id}`, data);
        return response.data;
    },

    /**
     * Delete a route.
     * @param id The ID of the route to delete.
     */
    deleteRoute: async (id: string): Promise<void> => {
        await apiClient.delete(`/routes/${id}`);
    },

    /**
     * Finalise a route.
     * @param id The ID of the route to finalise.
     * @param data The data to finalise the route with.
     * @returns The finalised route.
     */
    finaliseRoute: async (id: string, data: RouteUpdate): Promise<RouteResponse> => {
        const response = await apiClient.post<RouteResponse>(`/routes/${id}/finalise`, data);
        return response.data;
    },

    /**
     * Submit a waypoint.
     *
     * @param data The data to submit a waypoint with.
     * @returns The submitted waypoint.
     */
    submitWaypoint: async (data: WaypointCreate): Promise<WaypointResponse> => {
        const response = await apiClient.post<WaypointResponse>('/waypoints/', data);
        return response.data;
    },

    /**
     * Get all waypoints for a route.
     * @param routeId The ID of the route.
     * @returns The waypoints ordered by stored_at.
     */
    getWaypoints: async (routeId: string): Promise<WaypointResponse[]> => {
        const response = await apiClient.get<WaypointResponse[]>(`/routes/${routeId}/waypoints`);
        return response.data;
    },

    /**
     * Generate a new travelogue for a route.
     * @param routeId The ID of the route to generate a travelogue for.
     * @param config Optional model and prompt type overrides.
     * @returns The generated travelogue.
     */
    generateTravelogue: async (routeId: string, config?: TravelogueCreate): Promise<TravelogueResponse> => {
        const response = await apiClient.post<TravelogueResponse>(`/generate/${routeId}`, config ?? {});
        return response.data;
    },

    /**
     * Get all travelogues for a route, each with embedded evaluation if evaluated.
     * @param routeId The ID of the route.
     * @returns Travelogues ordered newest-first.
     */
    getTravelogues: async (routeId: string): Promise<TravelogueResponse[]> => {
        const response = await apiClient.get<TravelogueResponse[]>(`/generate/${routeId}`);
        return response.data;
    },

    /**
     * List available Ollama models.
     * @returns Model names and the configured default.
     */
    getModels: async (): Promise<{ models: string[]; default: string }> => {
        const response = await apiClient.get<{ models: string[]; default: string }>('/generate/models');
        return response.data;
    },

    /**
     * Evaluate a route by comparing an AI travelogue against the human waypoint notes.
     * @param routeId The ID of the route to evaluate.
     * @param travelogueId Optional specific travelogue to evaluate; uses most recent if omitted.
     * @returns The evaluation.
     */
    evaluateRoute: async (routeId: string, travelogueId?: string): Promise<EvaluationResponse> => {
        const params = travelogueId ? { travelogue_id: travelogueId } : {};
        const response = await apiClient.post<EvaluationResponse>(`/evaluate/${routeId}`, {}, { params });
        return response.data;
    },

    /**
     * Get the stored evaluation for a route or specific travelogue.
     * @param routeId The ID of the route.
     * @param travelogueId Optional specific travelogue; falls back to legacy route-level eval if omitted.
     * @returns The stored evaluation, or throws 404 if none exists.
     */
    getEvaluation: async (routeId: string, travelogueId?: string): Promise<EvaluationResponse> => {
        const params = travelogueId ? { travelogue_id: travelogueId } : {};
        const response = await apiClient.get<EvaluationResponse>(`/evaluate/${routeId}`, { params });
        return response.data;
    },

    /**
     * Health check.
     *
     * This doesn't typically get triggered from the FE, but adding
     * an integration here for convience during testing.
     */
    healthCheck: async (): Promise<void> => {
        await apiClient.get('/health');
    }
};
