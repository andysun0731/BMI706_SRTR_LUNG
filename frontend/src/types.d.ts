declare module 'react-simple-maps' {
    import { ComponentType, ReactNode } from 'react';

    interface ComposableMapProps {
        projection?: string;
        projectionConfig?: {
            scale?: number;
            center?: [number, number];
            rotate?: [number, number, number];
        };
        width?: number;
        height?: number;
        style?: React.CSSProperties;
        children?: ReactNode;
    }

    interface GeographiesProps {
        geography: string | object;
        children: (data: { geographies: any[] }) => ReactNode;
    }

    interface GeographyProps {
        geography: any;
        fill?: string;
        stroke?: string;
        strokeWidth?: number;
        style?: {
            default?: React.CSSProperties;
            hover?: React.CSSProperties;
            pressed?: React.CSSProperties;
        };
    }

    interface MarkerProps {
        coordinates: [number, number];
        onClick?: () => void;
        onMouseEnter?: () => void;
        onMouseLeave?: () => void;
        style?: React.CSSProperties;
        children?: ReactNode;
    }

    interface LineProps {
        from: [number, number];
        to: [number, number];
        stroke?: string;
        strokeWidth?: number;
        strokeOpacity?: number;
    }

    export const ComposableMap: ComponentType<ComposableMapProps>;
    export const Geographies: ComponentType<GeographiesProps>;
    export const Geography: ComponentType<GeographyProps>;
    export const Marker: ComponentType<MarkerProps>;
    export const Line: ComponentType<LineProps>;
}

declare module 'rc-slider' {
    import { ComponentType } from 'react';

    interface SliderProps {
        range?: boolean;
        min?: number;
        max?: number;
        value?: number | [number, number];
        defaultValue?: number | [number, number];
        onChange?: (value: number | number[]) => void;
        trackStyle?: React.CSSProperties[];
        handleStyle?: React.CSSProperties[];
        railStyle?: React.CSSProperties;
        step?: number;
        marks?: Record<number, string | { label: string; style?: React.CSSProperties }>;
    }

    const Slider: ComponentType<SliderProps>;
    export default Slider;
}
