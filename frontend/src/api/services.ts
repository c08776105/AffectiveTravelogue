import { apiClient } from './client';
import type {
    RouteCreate, RouteResponse, RouteUpdate,
    WaypointCreate, WaypointResponse,
    EvaluationCreate, EvaluationResponse
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
     * Generate a travelogue.
     * 
     * This doesn't typically get triggered from the FE, but adding
     * an integration here for convience during testing.
     * 
     * @param routeId The ID of the route to generate a travelogue for.
     */
    generateTravelogue: async (routeId: string): Promise<void> => {
        await apiClient.post(`/generate/${routeId}`);
    },

    /**
     * Evaluate a route.
     * 
     * This doesn't typically get triggered from the FE, but adding
     * an integration here for convience during testing.
     * 
     * @param routeId The ID of the route to evaluate.
     * @param data The data to evaluate the route with.
     * @returns The evaluation.
     */
    evaluateRoute: async (routeId: string, data: EvaluationCreate): Promise<EvaluationResponse> => {
        const response = await apiClient.post<EvaluationResponse>(`/evaluate/${routeId}`, data);
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
