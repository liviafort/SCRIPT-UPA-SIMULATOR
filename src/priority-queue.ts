import { Patient, ClassificacaoManchester } from './types';

export class PriorityQueue {
  private queue: Patient[] = [];
  private readonly priorityOrder: Record<ClassificacaoManchester, number> = {
    'VERMELHO': 1,
    'AMARELO': 2,
    'VERDE': 3,
    'AZUL': 4
  };

  enqueue(patient: Patient): void {
    const patientWithQueueTime = {
      ...patient,
      queueEntryTime: Date.now()
    };

    this.queue.push(patientWithQueueTime as Patient);

    this.queue.sort((a, b) => {
      const priorityA = this.priorityOrder[a.classificacao];
      const priorityB = this.priorityOrder[b.classificacao];

      if (priorityA !== priorityB) {
        return priorityA - priorityB;
      }

      const timeA = (a as any).queueEntryTime || 0;
      const timeB = (b as any).queueEntryTime || 0;
      return timeA - timeB;
    });
  }

  dequeue(): Patient | undefined {
    return this.queue.shift();
  }

  size(): number {
    return this.queue.length;
  }

  isEmpty(): boolean {
    return this.queue.length === 0;
  }

  getStats(): Record<ClassificacaoManchester, number> {
    const stats: Record<ClassificacaoManchester, number> = {
      'VERMELHO': 0,
      'AMARELO': 0,
      'VERDE': 0,
      'AZUL': 0
    };

    for (const patient of this.queue) {
      stats[patient.classificacao]++;
    }

    return stats;
  }
}
