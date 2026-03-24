import { Request, Response } from 'express';
import * as problemService from '../services/problemService';

export const getProblems = async (req: Request, res: Response) => {
  const data = await problemService.getAllProblems();
  res.json({ success: true, data });
};