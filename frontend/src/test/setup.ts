/**
 * Vitest Test Setup
 * Sprint 15: Frontend testing configuration
 */

import { expect, afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import * as matchers from '@testing-library/jest-dom/matchers';

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers);

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock react-force-graph to prevent loading of 3D dependencies (aframe, three.js)
// This prevents "AFRAME is not defined" and "THREE is not defined" errors
vi.mock('react-force-graph', () => {
  return {
    default: vi.fn(),
    ForceGraph2D: vi.fn((props: any) => null),
    ForceGraph3D: vi.fn(() => null),
    ForceGraphVR: vi.fn(() => null),
    ForceGraphAR: vi.fn(() => null),
  };
});

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return [];
  }
  unobserve() {}
} as any;

// Mock AFRAME global for aframe-extras (transitive dependency of react-force-graph)
// AFRAME is used by 3d-force-graph-vr and 3d-force-graph-ar packages
(global as any).AFRAME = {
  registerComponent: vi.fn(),
  registerPrimitive: vi.fn(),
  registerShader: vi.fn(),
  registerGeometry: vi.fn(),
  registerSystem: vi.fn(),
  utils: {
    entity: {
      setComponentProperty: vi.fn(),
    },
    coordinates: {
      parse: vi.fn(),
    },
  },
  components: {},
  primitives: {
    primitives: {},
  },
  scenes: [],
};

// Mock THREE.js global for aframe-extras (transitive dependency of react-force-graph)
// Create a minimal THREE.js mock to satisfy aframe-extras requirements
const createVectorMock = (dimensions: number) => vi.fn().mockImplementation(function (...args: number[]) {
  for (let i = 0; i < dimensions; i++) {
    (this as any)[['x', 'y', 'z', 'w'][i]] = args[i] || 0;
  }
  this.set = vi.fn().mockReturnThis();
  this.copy = vi.fn().mockReturnThis();
  this.add = vi.fn().mockReturnThis();
  this.sub = vi.fn().mockReturnThis();
  this.multiply = vi.fn().mockReturnThis();
  this.multiplyScalar = vi.fn().mockReturnThis();
  this.length = vi.fn().mockReturnValue(0);
  this.normalize = vi.fn().mockReturnThis();
  this.clone = vi.fn().mockReturnThis();
  this.applyMatrix4 = vi.fn().mockReturnThis();
  this.setFromMatrixPosition = vi.fn().mockReturnThis();
  return this;
});

(global as any).THREE = {
  Vector2: createVectorMock(2),
  Vector3: createVectorMock(3),
  Quaternion: vi.fn().mockImplementation(function () {
    this.setFromAxisAngle = vi.fn().mockReturnThis();
    this.setFromRotationMatrix = vi.fn().mockReturnThis();
    this.multiply = vi.fn().mockReturnThis();
    return this;
  }),
  Euler: vi.fn().mockImplementation(function () {
    this.setFromQuaternion = vi.fn().mockReturnThis();
    return this;
  }),
  Matrix4: vi.fn().mockImplementation(function () {
    this.identity = vi.fn().mockReturnThis();
    this.makeRotationFromQuaternion = vi.fn().mockReturnThis();
    return this;
  }),
  Box3: vi.fn().mockImplementation(function () {
    this.setFromObject = vi.fn().mockReturnThis();
    this.getCenter = vi.fn().mockReturnValue({ x: 0, y: 0, z: 0 });
    this.getSize = vi.fn().mockReturnValue({ x: 1, y: 1, z: 1 });
    this.expandByPoint = vi.fn().mockReturnThis();
    return this;
  }),
  Raycaster: vi.fn().mockImplementation(function () {
    this.set = vi.fn();
    this.intersectObject = vi.fn().mockReturnValue([]);
    this.intersectObjects = vi.fn().mockReturnValue([]);
    return this;
  }),
  Object3D: vi.fn().mockImplementation(function () {
    this.position = { x: 0, y: 0, z: 0, set: vi.fn() };
    this.rotation = { x: 0, y: 0, z: 0, set: vi.fn() };
    this.scale = { x: 1, y: 1, z: 1, set: vi.fn() };
    this.quaternion = { set: vi.fn(), setFromAxisAngle: vi.fn() };
    this.getWorldPosition = vi.fn().mockReturnValue({ x: 0, y: 0, z: 0 });
    this.getWorldQuaternion = vi.fn().mockReturnValue({ x: 0, y: 0, z: 0, w: 1 });
    return this;
  }),
  Mesh: vi.fn(),
  Material: vi.fn(),
  Geometry: vi.fn(),
  AnimationMixer: vi.fn().mockImplementation(function () {
    this.update = vi.fn();
    this.clipAction = vi.fn().mockReturnValue({
      play: vi.fn(),
      stop: vi.fn(),
      setEffectiveWeight: vi.fn(),
    });
    return this;
  }),
  // Animation constants
  LoopOnce: 2200,
  LoopRepeat: 2201,
  LoopPingPong: 2202,
};
