// isend_irecv
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

#define TAG 13

int main(int argc, char *argv[]) {
   int myid, numprocs, left, right;
    int buf, buff2 = 5;
    MPI_Request request, request2, request3, request4;
    MPI_Status status1,status2,status3,status4;

    MPI_Init(&argc,&argv);
    MPI_Comm_size(MPI_COMM_WORLD, &numprocs);
    MPI_Comm_rank(MPI_COMM_WORLD, &myid);
    right = (myid + 1) % numprocs;
    left = myid - 1;
    if (left < 0)
        left = numprocs - 1;
    if(myid == 1){
        usleep(300000);
    }
    MPI_Irecv(&buf, 1, MPI_INT, left, 123, MPI_COMM_WORLD, &request);
    if(myid == 1){
        usleep(300000);
    }
    MPI_Isend(&buff2, 1, MPI_INT, right, 123, MPI_COMM_WORLD, &request2);
    if(myid == 1){
        usleep(300000);
    }
    MPI_Irecv(&buf, 1, MPI_INT, left, 125, MPI_COMM_WORLD, &request3);
    if(myid == 1){
        usleep(300000);
    }
    MPI_Isend(&buff2, 1, MPI_INT, right, 125, MPI_COMM_WORLD, &request4);
    if(myid == 1){
        usleep(300000);
    }
    MPI_Wait(&request3, &status1);
    if(myid == 1){
        usleep(600000);
    }
    MPI_Wait(&request4, &status2);
    if(myid == 1){
        usleep(300000);
    }
    MPI_Wait(&request2, &status3);
    if(myid == 1){
        usleep(600000);
    }
    MPI_Wait(&request, &status4);
    if(myid == 1){
        usleep(300000);
    }
    MPI_Barrier(MPI_COMM_WORLD);
    if(myid == 2){
        usleep(300000);
    }
    MPI_Finalize();
    return 0;
}
