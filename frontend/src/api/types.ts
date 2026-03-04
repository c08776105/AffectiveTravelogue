export interface RouteCreate {
    name: string;
    startLat: number;
    startLon: number;
    endLat?: number | null;
    endLon?: number | null;
    distanceKm?: number | null;
    derivePoints?: number | null;
    deviationMeters?: number | null;
}

export interface RouteResponse {
    id: string;
    name: string;
    startLat: number;
    startLon: number;
    endLat?: number | null;
    endLon?: number | null;
    distanceKm?: number | null;
    derivePoints?: number | null;
    deviationMeters?: number | null;
    createdAt: string;
    status: string;
    waypointCount?: number | null;
}

export interface RouteUpdate {
    name?: string | null;
    status?: string | null;
    endLat?: number | null;
    endLon?: number | null;
    distanceKm?: number | null;
}

export interface WaypointCreate {
    latitude: number;
    longitude: number;
    textNote?: string | null;
    voiceBlobUrl?: string | null;
    imageUrl?: string | null;
    routeId: string;
}

export interface WaypointResponse {
    id: string;
    latitude: number;
    longitude: number;
    textNote?: string | null;
    voiceBlobUrl?: string | null;
    imageUrl?: string | null;
    transcription?: string | null;
    storedAt: string;
}

export interface EvaluationCreate {
    routeId: string;
    humanJournal: string;
}

export interface EvaluationResponse {
    bertscoreF1: number;
    bertscorePrecision: number;
    bertscoreRecall: number;
    isEquivalent: boolean;
    humanSentiment: number;
    aiSentiment: number;
    createdAt: string;
}
