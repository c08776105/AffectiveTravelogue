// Geographic Types
export interface LatLng {
    lat: number
    lng: number
}

// Domain Types
export interface Observation {
    id?: string
    timestamp?: number
    location?: LatLng
    type: 'note' | 'photo' | 'voice' | 'text'
    content?: string
    text?: string
    audioData?: string
    imageData?: string
    caption?: string
}

export interface Route {
    id: string
    [key: string]: any
}

export interface Walk {
    id: string
    startTime: number
    endTime?: number
    title: string
    mood: string
    path: LatLng[]
    observations: Observation[]
    distance: number
    duration: number
    isActive: boolean
}
