import {request} from './client';import {Feature} from '../types/domain';export const getFeatures=(id:number)=>request<Feature[]>(`/studies/${id}/features`);
