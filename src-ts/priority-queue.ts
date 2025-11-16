import { Patient, ClassificacaoManchester } from './types';

/**
 * Fila de prioridade para pacientes seguindo Protocolo de Manchester
 * Ordem: VERMELHO > AMARELO > VERDE > AZUL
 * Dentro da mesma prioridade: FIFO (First In, First Out)
 */
export class PriorityQueue {
  private queue: Patient[] = [];
  private readonly priorityOrder: Record<ClassificacaoManchester, number> = {
    'VERMELHO': 1,
    'AMARELO': 2,
    'VERDE': 3,
    'AZUL': 4
  };

  /**
   * Adiciona paciente à fila respeitando ordem de prioridade
   */
  enqueue(patient: Patient): void {
    // Adiciona timestamp de entrada na fila para desempate FIFO
    const patientWithQueueTime = {
      ...patient,
      queueEntryTime: Date.now()
    };

    this.queue.push(patientWithQueueTime as Patient);

    // Ordena: primeiro por prioridade, depois por ordem de chegada (FIFO)
    this.queue.sort((a, b) => {
      const priorityA = this.priorityOrder[a.classificacao];
      const priorityB = this.priorityOrder[b.classificacao];

      if (priorityA !== priorityB) {
        return priorityA - priorityB; // Menor número = maior prioridade
      }

      // Mesma prioridade: FIFO (quem entrou primeiro sai primeiro)
      const timeA = (a as any).queueEntryTime || 0;
      const timeB = (b as any).queueEntryTime || 0;
      return timeA - timeB;
    });
  }

  /**
   * Remove e retorna paciente com maior prioridade
   */
  dequeue(): Patient | undefined {
    return this.queue.shift();
  }

  /**
   * Retorna tamanho atual da fila
   */
  size(): number {
    return this.queue.length;
  }

  /**
   * Verifica se fila está vazia
   */
  isEmpty(): boolean {
    return this.queue.length === 0;
  }

  /**
   * Retorna estatísticas da fila por classificação
   */
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
