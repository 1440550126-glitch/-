import { create } from 'zustand';
import type { Project } from '@/types/studio';
type State = { current?: Project; setCurrent: (project: Project) => void };
export const useProjectStore = create<State>((set) => ({ setCurrent: (project) => set({ current: project }) }));
