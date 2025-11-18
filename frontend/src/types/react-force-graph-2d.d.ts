/**
 * Type definitions for react-force-graph-2d
 * Sprint 29 Feature 29.1: Custom type declarations
 */

declare module 'react-force-graph-2d' {
  import { Component, RefObject } from 'react';

  export interface NodeObject {
    id?: string | number;
    x?: number;
    y?: number;
    vx?: number;
    vy?: number;
    fx?: number | null;
    fy?: number | null;
    [key: string]: any;
  }

  export interface LinkObject {
    source?: string | number | NodeObject;
    target?: string | number | NodeObject;
    [key: string]: any;
  }

  export interface GraphData {
    nodes: NodeObject[];
    links: LinkObject[];
  }

  export interface ForceGraphMethods {
    d3Force: (forceName: string, force?: any) => any;
    d3ReheatSimulation: () => void;
    emitParticle: (link: LinkObject) => void;
    getGraphBbox: () => { x: [number, number]; y: [number, number] };
    pauseAnimation: () => void;
    resumeAnimation: () => void;
    centerAt: (x?: number, y?: number, duration?: number) => void;
    zoom: (scale: number, duration?: number) => void;
    zoomToFit: (duration?: number, padding?: number) => void;
    screen2GraphCoords: (x: number, y: number) => { x: number; y: number };
    graph2ScreenCoords: (x: number, y: number) => { x: number; y: number };
  }

  export interface ForceGraphProps {
    // Data
    graphData?: GraphData;
    nodeId?: string;
    linkSource?: string;
    linkTarget?: string;

    // Container
    width?: number;
    height?: number;
    backgroundColor?: string;

    // Node styling
    nodeRelSize?: number;
    nodeVal?: number | string | ((node: NodeObject) => number);
    nodeLabel?: string | ((node: NodeObject) => string);
    nodeColor?: string | ((node: NodeObject) => string);
    nodeAutoColorBy?: string | ((node: NodeObject) => string);
    nodeCanvasObject?: (node: NodeObject, ctx: CanvasRenderingContext2D, globalScale: number) => void;
    nodeCanvasObjectMode?: string | ((node: NodeObject) => string);

    // Link styling
    linkLabel?: string | ((link: LinkObject) => string);
    linkColor?: string | ((link: LinkObject) => string);
    linkAutoColorBy?: string | ((link: LinkObject) => string);
    linkWidth?: number | string | ((link: LinkObject) => number);
    linkDirectionalArrowLength?: number | string | ((link: LinkObject) => number);
    linkDirectionalArrowRelPos?: number | string | ((link: LinkObject) => number);
    linkDirectionalArrowColor?: string | ((link: LinkObject) => string);
    linkDirectionalParticles?: number | string | ((link: LinkObject) => number);
    linkDirectionalParticleSpeed?: number | string | ((link: LinkObject) => number);
    linkDirectionalParticleWidth?: number | string | ((link: LinkObject) => number);
    linkDirectionalParticleColor?: string | ((link: LinkObject) => string);
    linkCanvasObject?: (link: LinkObject, ctx: CanvasRenderingContext2D, globalScale: number) => void;
    linkCanvasObjectMode?: string | ((link: LinkObject) => string);

    // Force simulation
    d3AlphaDecay?: number;
    d3AlphaMin?: number;
    d3VelocityDecay?: number;
    warmupTicks?: number;
    cooldownTicks?: number;
    cooldownTime?: number;

    // Interaction
    onNodeClick?: (node: NodeObject, event: MouseEvent) => void;
    onNodeRightClick?: (node: NodeObject, event: MouseEvent) => void;
    onNodeHover?: (node: NodeObject | null, previousNode: NodeObject | null) => void;
    onNodeDrag?: (node: NodeObject, translate: { x: number; y: number }) => void;
    onNodeDragEnd?: (node: NodeObject, translate: { x: number; y: number }) => void;
    onLinkClick?: (link: LinkObject, event: MouseEvent) => void;
    onLinkRightClick?: (link: LinkObject, event: MouseEvent) => void;
    onLinkHover?: (link: LinkObject | null, previousLink: LinkObject | null) => void;
    onBackgroundClick?: (event: MouseEvent) => void;
    onBackgroundRightClick?: (event: MouseEvent) => void;
    onZoom?: (transform: { k: number; x: number; y: number }) => void;
    onZoomEnd?: (transform: { k: number; x: number; y: number }) => void;

    // Interaction settings
    enableNodeDrag?: boolean;
    enableZoomInteraction?: boolean;
    enablePanInteraction?: boolean;
    enablePointerInteraction?: boolean;
    enableNavigationControls?: boolean;

    // Misc
    minZoom?: number;
    maxZoom?: number;
    onRenderFramePre?: (ctx: CanvasRenderingContext2D, globalScale: number) => void;
    onRenderFramePost?: (ctx: CanvasRenderingContext2D, globalScale: number) => void;
  }

  export default class ForceGraph2D extends Component<ForceGraphProps> {
    // Methods
    d3Force(forceName: string, force?: any): any;
    d3ReheatSimulation(): void;
    emitParticle(link: LinkObject): void;
    getGraphBbox(): { x: [number, number]; y: [number, number] };
    pauseAnimation(): void;
    resumeAnimation(): void;
    centerAt(x?: number, y?: number, duration?: number): void;
    zoom(scale: number, duration?: number): void;
    zoomToFit(duration?: number, padding?: number): void;
    screen2GraphCoords(x: number, y: number): { x: number; y: number };
    graph2ScreenCoords(x: number, y: number): { x: number; y: number };
  }
}
